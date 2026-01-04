"""
Pydantic schemas for payment endpoints.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from src.models.models import (
    SubscriptionPlan,
    BillingCycle,
    PaymentProvider,
    PaymentStatus,
    SubscriptionStatus,
)


# ==================== REQUEST SCHEMAS ====================

class InitializePaymentRequest(BaseModel):
    """Request to initialize a payment for subscription."""
    plan: SubscriptionPlan
    billing_cycle: BillingCycle
    provider: PaymentProvider
    callback_url: Optional[str] = None  # Override default callback URL


class VerifyPaymentRequest(BaseModel):
    """Request to verify a payment."""
    reference: str


class CancelSubscriptionRequest(BaseModel):
    """Request to cancel subscription."""
    reason: Optional[str] = None


# ==================== RESPONSE SCHEMAS ====================

class InitializePaymentResponse(BaseModel):
    """Response after initializing a payment."""
    reference: str
    authorization_url: str
    provider: PaymentProvider
    amount: Decimal
    currency: str = "NGN"


class PaymentVerificationResponse(BaseModel):
    """Response after verifying a payment."""
    reference: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    plan: SubscriptionPlan
    billing_cycle: BillingCycle
    message: str


class SubscriptionResponse(BaseModel):
    """User's subscription details."""
    id: UUID
    plan: SubscriptionPlan
    billing_cycle: Optional[BillingCycle] = None
    status: SubscriptionStatus
    start_date: datetime
    end_date: Optional[datetime] = None
    auto_renew: bool
    payment_provider: Optional[PaymentProvider] = None

    class Config:
        from_attributes = True


class PaymentTransactionResponse(BaseModel):
    """Payment transaction details."""
    id: UUID
    reference: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    plan: SubscriptionPlan
    billing_cycle: BillingCycle
    provider: PaymentProvider
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== PRICING CONFIG ====================

class PlanPricing(BaseModel):
    """Pricing for a subscription plan."""
    plan: SubscriptionPlan
    monthly_price: Decimal  # In Naira
    yearly_price: Decimal   # In Naira
    currency: str = "NGN"


# Pricing configuration (can be moved to config/settings later)
PLAN_PRICING = {
    SubscriptionPlan.FREE: PlanPricing(
        plan=SubscriptionPlan.FREE,
        monthly_price=Decimal("0"),
        yearly_price=Decimal("0"),
    ),
    SubscriptionPlan.FOCUSED: PlanPricing(
        plan=SubscriptionPlan.FOCUSED,
        monthly_price=Decimal("700"),
        yearly_price=Decimal("6000"),
    ),
    SubscriptionPlan.PRO: PlanPricing(
        plan=SubscriptionPlan.PRO,
        monthly_price=Decimal("1500"),
        yearly_price=Decimal("12000"),
    ),
}


def get_plan_amount(plan: SubscriptionPlan, billing_cycle: BillingCycle) -> Decimal:
    """Get the amount for a plan and billing cycle."""
    pricing = PLAN_PRICING.get(plan)
    if not pricing:
        raise ValueError(f"Unknown plan: {plan}")
    
    if billing_cycle == BillingCycle.MONTHLY:
        return pricing.monthly_price
    else:
        return pricing.yearly_price
