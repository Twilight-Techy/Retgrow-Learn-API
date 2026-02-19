"""
Subscription service handling subscription logic.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.models import (
    User,
    Subscription,
    SubscriptionPlan,
    BillingCycle,
    PaymentProvider,
    SubscriptionStatus,
)
from src.modules.payments.schemas import get_plan_amount


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
                or_(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    and_(
                        Subscription.status == SubscriptionStatus.CANCELLED,
                        Subscription.end_date > datetime.utcnow()
                    )
                )
            )
        )
        .order_by(Subscription.created_at.desc())
    )
    return result.scalars().first()


async def get_best_valid_subscription(
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Optional[Subscription]:
    """
    Get the highest priority valid subscription for access control.
    Priority: PRO > FOCUSED > FREE.
    """
    # 1. Fetch all valid subscriptions
    stmt = select(Subscription).where(
        and_(
            Subscription.user_id == user_id,
            or_(
                Subscription.status == SubscriptionStatus.ACTIVE,
                and_(
                    Subscription.status == SubscriptionStatus.CANCELLED,
                    Subscription.end_date > datetime.utcnow()
                )
            )
        )
    )
    result = await db.execute(stmt)
    subscriptions = result.scalars().all()
    
    if not subscriptions:
        return None
        
    # 2. Sort by priority
    # Define priority map
    PRIORITY = {
        SubscriptionPlan.PRO: 3,
        SubscriptionPlan.FOCUSED: 2,
        SubscriptionPlan.FREE: 1
    }
    
    # Sort descending by priority, then descending by created_at (newest first for ties)
    sorted_subs = sorted(
        subscriptions, 
        key=lambda s: (PRIORITY.get(s.plan, 0), s.created_at), 
        reverse=True
    )
    
    return sorted_subs[0]


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


async def create_new_subscription_record(
    user_id: uuid.UUID,
    plan: SubscriptionPlan,
    billing_cycle: BillingCycle,
    provider: PaymentProvider,
    db: AsyncSession,
) -> Subscription:
    """
    Create a new subscription record, cancelling any existing active one.
    This is used when upgrading/downgrading or activating a new subscription.
    """
    # 1. Find and cancel existing active subscription
    current_subscription = await get_active_subscription(user_id, db)
    if current_subscription:
        current_subscription.status = SubscriptionStatus.CANCELLED
        db.add(current_subscription)
    
    # 2. Create new subscription
    new_subscription = Subscription(
        user_id=user_id,
        plan=plan,
        billing_cycle=billing_cycle,
        status=SubscriptionStatus.ACTIVE,
        start_date=datetime.utcnow(),
        end_date=calculate_end_date(billing_cycle),
        payment_provider=provider,
        auto_renew=True
    )
    
    db.add(new_subscription)
    await db.commit()
    await db.refresh(new_subscription)
    
    return new_subscription
