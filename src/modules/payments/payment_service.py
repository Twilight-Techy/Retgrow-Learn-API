"""
Payment service handling subscription and transaction logic.
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.models import (
    User,
    Subscription,
    PaymentTransaction,
    SubscriptionPlan,
    BillingCycle,
    PaymentProvider,
    PaymentStatus,
    SubscriptionStatus,
)
from .schemas import get_plan_amount
from .providers.base import BasePaymentProvider
from .providers.paystack import PaystackProvider
from .providers.opay import OPayProvider
from .providers.stripe_provider import StripeProvider


# Provider registry
PROVIDERS: Dict[PaymentProvider, BasePaymentProvider] = {
    PaymentProvider.PAYSTACK: PaystackProvider(),
    PaymentProvider.OPAY: OPayProvider(),
    PaymentProvider.STRIPE: StripeProvider(),
}


def get_provider(provider: PaymentProvider) -> BasePaymentProvider:
    """Get the payment provider instance."""
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown payment provider: {provider}")
    return PROVIDERS[provider]


def generate_reference() -> str:
    """Generate a unique payment reference."""
    return f"RL-{uuid.uuid4().hex[:16].upper()}"


def calculate_end_date(billing_cycle: BillingCycle) -> datetime:
    """Calculate subscription end date based on billing cycle."""
    now = datetime.utcnow()
    if billing_cycle == BillingCycle.MONTHLY:
        return now + timedelta(days=30)
    else:
        return now + timedelta(days=365)


async def get_active_subscription(
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Optional[Subscription]:
    """Get user's active subscription."""
    result = await db.execute(
        select(Subscription)
        .where(
            and_(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        .order_by(Subscription.created_at.desc())
    )
    return result.scalars().first()


async def get_or_create_subscription(
    user: User,
    db: AsyncSession,
) -> Subscription:
    """Get existing subscription or create a free one."""
    subscription = await get_active_subscription(user.id, db)
    
    if not subscription:
        # Create a free subscription for the user
        subscription = Subscription(
            user_id=user.id,
            plan=SubscriptionPlan.FREE,
            status=SubscriptionStatus.ACTIVE,
        )
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
    
    return subscription


async def initialize_payment(
    user: User,
    plan: SubscriptionPlan,
    billing_cycle: BillingCycle,
    provider: PaymentProvider,
    callback_url: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Initialize a payment for subscription upgrade.
    
    Returns dict with authorization_url, reference, etc.
    """
    if plan == SubscriptionPlan.FREE:
        raise ValueError("Cannot pay for free plan")
    
    # Get amount for the plan
    amount = get_plan_amount(plan, billing_cycle)
    
    if amount <= 0:
        raise ValueError("Invalid plan amount")
    
    # Generate unique reference
    reference = generate_reference()
    
    # Create pending transaction
    transaction = PaymentTransaction(
        user_id=user.id,
        amount=amount,
        currency="NGN",
        provider=provider,
        reference=reference,
        status=PaymentStatus.PENDING,
        plan=plan,
        billing_cycle=billing_cycle,
        payment_metadata={
            "email": user.email,
            "user_name": f"{user.first_name} {user.last_name}",
        },
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    
    # Initialize with payment provider
    payment_provider = get_provider(provider)
    result = await payment_provider.initialize_payment(
        amount=amount,
        email=user.email,
        reference=reference,
        callback_url=callback_url,
        metadata={
            "plan": plan.value,
            "billing_cycle": billing_cycle.value,
            "user_id": str(user.id),
            "user_name": f"{user.first_name} {user.last_name}",
            "user_info": {
                "user_id": str(user.id),
                "user_name": f"{user.first_name} {user.last_name}",
            },
        },
    )
    
    if not result.success:
        # Mark transaction as failed
        transaction.status = PaymentStatus.FAILED
        transaction.payment_metadata = {
            **(transaction.payment_metadata or {}),
            "error": result.error_message,
        }
        await db.commit()
        raise ValueError(result.error_message or "Failed to initialize payment")
    
    # Update transaction with external reference
    transaction.external_reference = result.external_reference
    await db.commit()
    
    return {
        "reference": reference,
        "authorization_url": result.authorization_url,
        "provider": provider,
        "amount": amount,
        "currency": "NGN",
    }


async def verify_and_activate_subscription(
    reference: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Verify payment and activate subscription if successful.
    
    Called by webhook or manual verification.
    """
    # Find the transaction
    result = await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.reference == reference)
    )
    transaction = result.scalars().first()
    
    if not transaction:
        raise ValueError(f"Transaction not found: {reference}")
    
    # If already processed, return current status
    if transaction.status in [PaymentStatus.SUCCESS, PaymentStatus.FAILED]:
        return {
            "reference": reference,
            "status": transaction.status,
            "message": "Transaction already processed",
        }
    
    # Verify with payment provider
    provider = get_provider(transaction.provider)
    verify_result = await provider.verify_payment(reference)
    
    if verify_result.success:
        # Update transaction
        transaction.status = PaymentStatus.SUCCESS
        transaction.completed_at = datetime.utcnow()
        transaction.external_reference = verify_result.external_reference
        transaction.payment_metadata = {
            **(transaction.payment_metadata or {}),
            "verification_response": verify_result.raw_response,
        }
        
        # Create or update subscription
        subscription = await get_active_subscription(transaction.user_id, db)
        
        if subscription:
            # Upgrade existing subscription
            subscription.plan = transaction.plan
            subscription.billing_cycle = transaction.billing_cycle
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.start_date = datetime.utcnow()
            subscription.end_date = calculate_end_date(transaction.billing_cycle)
            subscription.payment_provider = transaction.provider
        else:
            # Create new subscription
            subscription = Subscription(
                user_id=transaction.user_id,
                plan=transaction.plan,
                billing_cycle=transaction.billing_cycle,
                status=SubscriptionStatus.ACTIVE,
                start_date=datetime.utcnow(),
                end_date=calculate_end_date(transaction.billing_cycle),
                payment_provider=transaction.provider,
            )
            db.add(subscription)
        
        # Link transaction to subscription
        await db.flush()
        transaction.subscription_id = subscription.id
        
        await db.commit()
        
        return {
            "reference": reference,
            "status": PaymentStatus.SUCCESS,
            "plan": transaction.plan,
            "billing_cycle": transaction.billing_cycle,
            "message": "Subscription activated successfully",
        }
    else:
        # Mark as failed
        transaction.status = PaymentStatus.FAILED
        transaction.payment_metadata = {
            **(transaction.payment_metadata or {}),
            "error": verify_result.error_message,
        }
        await db.commit()
        
        return {
            "reference": reference,
            "status": PaymentStatus.FAILED,
            "message": verify_result.error_message or "Payment verification failed",
        }


async def cancel_subscription(
    user_id: uuid.UUID,
    reason: Optional[str],
    db: AsyncSession,
) -> Dict[str, Any]:
    """Cancel user's active subscription."""
    subscription = await get_active_subscription(user_id, db)
    
    if not subscription:
        raise ValueError("No active subscription found")
    
    if subscription.plan == SubscriptionPlan.FREE:
        raise ValueError("Cannot cancel free plan")
    
    # Mark subscription as cancelled
    subscription.status = SubscriptionStatus.CANCELLED
    subscription.auto_renew = False
    
    await db.commit()
    
    return {
        "message": "Subscription cancelled. Access continues until end of billing period.",
        "end_date": subscription.end_date,
    }
