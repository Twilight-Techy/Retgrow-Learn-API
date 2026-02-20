
"""
Service for handling recurring subscription payments.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.models import (
    Subscription,
    SubscriptionStatus,
    PaymentTransaction,
    PaymentStatus,
    SubscriptionPlan,
    BillingCycle,
    PaymentProvider,
    User,
)
from src.modules.payments import payment_service
from src.modules.payments.schemas import get_plan_amount
# from src.common.email import send_email # Assuming email service exists

logger = logging.getLogger(__name__)

async def process_due_subscriptions(db: AsyncSession) -> Dict[str, Any]:
    """
    Find and charge subscriptions due for renewal.
    """
    now = datetime.utcnow()
    
    # 1. Broad Query: Find ALL potential due subscriptions
    # Criteria: Active/Expired, Auto-Renew, End Date passed (or imminent), Has Token
    stmt = select(Subscription).where(
        and_(
            or_(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.status == SubscriptionStatus.EXPIRED
            ),
            Subscription.auto_renew == True,
            Subscription.end_date <= now, # Due now or in the past
            Subscription.payment_token.isnot(None),
            Subscription.plan != SubscriptionPlan.FREE
        )
    )
    
    result = await db.execute(stmt.options(selectinload(Subscription.user)))
    all_subscriptions = result.scalars().all()
    
    # 2. In-Memory Filter: Group by User ID and pick the BEST ONE
    # We want the most recent ACTIVE one. If none, the most recent EXPIRED one.
    # Effectively: Sort by (is_active, created_at) descending.
    
    subs_by_user: Dict[uuid.UUID, List[Subscription]] = {}
    for sub in all_subscriptions:
        if sub.user_id not in subs_by_user:
            subs_by_user[sub.user_id] = []
        subs_by_user[sub.user_id].append(sub)
        
    subscriptions_to_process = []
    
    for user_id, user_subs in subs_by_user.items():
        # Sort key: 
        # 1. Status is ACTIVE (True > False)
        # 2. Created At (Newer > Older)
        best_sub = sorted(
            user_subs,
            key=lambda s: (s.status == SubscriptionStatus.ACTIVE, s.created_at),
            reverse=True
        )[0]
        subscriptions_to_process.append(best_sub)
    
    results = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "details": []
    }
    
    for sub in subscriptions_to_process:
        results["processed"] += 1
        try:
            success = await renew_subscription(sub, sub.user, db)
            if success:
                results["success"] += 1
                results["details"].append(f"Renewed: {sub.id} ({sub.user_id})")
            else:
                results["failed"] += 1
                results["details"].append(f"Failed: {sub.id} ({sub.user_id})")
        except Exception as e:
            logger.error(f"Error renewing subscription {sub.id}: {str(e)}")
            results["failed"] += 1
            results["details"].append(f"Error: {sub.id} - {str(e)}")
            
    return results

async def renew_subscription(subscription: Subscription, user: User, db: AsyncSession) -> bool:
    """
    Attempt to charge and renew a single subscription.
    User is passed in (pre-loaded) to avoid per-subscription DB lookups.
    """
    if not user:
        logger.error(f"User not found for subscription {subscription.id}")
        return False

    # Calculate amount
    amount = get_plan_amount(subscription.plan, subscription.billing_cycle)
    
    # Generate reference
    reference = payment_service.generate_reference()
    
    # Get provider
    if not subscription.payment_provider:
        # Default to Paystack if missing (legacy?)
        subscription.payment_provider = PaymentProvider.PAYSTACK
        
    provider = payment_service.get_provider(subscription.payment_provider)
    
    # Attempt charge
    result = await provider.charge_subscription(
        amount=amount,
        email=user.email,
        authorization_code=subscription.payment_token,
        reference=reference,
        metadata={
            "subscription_id": str(subscription.id),
            "type": "renewal"
        }
    )
    
    # Record transaction
    transaction = PaymentTransaction(
        user_id=user.id,
        subscription_id=subscription.id,
        amount=amount,
        currency="NGN",
        provider=subscription.payment_provider,
        reference=reference,
        external_reference=result.external_reference,
        status=PaymentStatus.SUCCESS if result.success else PaymentStatus.FAILED,
        plan=subscription.plan,
        billing_cycle=subscription.billing_cycle,
        payment_metadata={
            "type": "renewal",
            "error": result.error_message
        }
    )
    db.add(transaction)
    
    if result.success:
        # Extend subscription
        # Calculate new end date from current end date (to avoid gaps/overlaps)
        # OR from now? Usually from current end_date if it's recent, or now if it's long expired.
        # Let's simple: From NOW. (Fail-safe).
        # Better: From max(now, end_date)?
        # If expired 3 days ago, and we renew now, we should probably start from now?
        # Or if we want strict cycles, we add to end_date.
        # "Netflix style": Service stops, pay, starts from payment date.
        # Since we have grace period, let's just create new period starting NOW.
        
        new_end_date = payment_service.calculate_end_date(subscription.billing_cycle)
        
        subscription.end_date = new_end_date
        subscription.status = SubscriptionStatus.ACTIVE # Re-activate if it was lazily expired (though query filters ACTIVE, lazy expiry might happen in get_active... wait, direct query used here)
        
        # If it was active, it stays active.
        # Note: If duplicate cron runs?
        # We checked end_date <= now.
        # Now we set end_date > now.
        # So it won't be picked up again.
        
        await db.commit()
        logger.info(f"Subscription {subscription.id} renewed until {new_end_date}")
        
        # Send renewal success email
        try:
            from src.common.utils.email_service import send_subscription_email
            
            context_data = {
                "plan_name": subscription.plan.value.capitalize(),
                "billing_cycle": subscription.billing_cycle.value.capitalize(),
                "amount": f"NGN {amount:,.2f}",
                "date": datetime.utcnow().strftime("%B %d, %Y"),
                "next_renewal_date": new_end_date.strftime("%B %d, %Y")
            }
            await send_subscription_email(
                type="renewed",
                user_email=user.email,
                user_first_name=user.first_name,
                context_data=context_data
            )
        except Exception as e:
            logger.error(f"Failed to send renewal email: {e}")
            
        return True
    else:
        # Payment failed
        await db.commit()
        logger.warning(f"Subscription {subscription.id} renewal failed: {result.error_message}")
        
        # Send failure email
        try:
            from src.common.utils.email_service import send_subscription_email
            
            context_data = {
                "plan_name": subscription.plan.value.capitalize(),
                "failure_reason": result.error_message or "Insufficient funds or card error"
            }
            await send_subscription_email(
                type="failed",
                user_email=user.email,
                user_first_name=user.first_name,
                context_data=context_data
            )
        except Exception as e:
            logger.error(f"Failed to send failed renewal email: {e}")
            
        return False
