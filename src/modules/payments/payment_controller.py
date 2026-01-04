"""
Payment API endpoints.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.database import get_db_session
from src.models.models import User, PaymentProvider, PaymentStatus
from src.auth.dependencies import get_current_user

from . import payment_service
from .schemas import (
    InitializePaymentRequest,
    InitializePaymentResponse,
    PaymentVerificationResponse,
    SubscriptionResponse,
    CancelSubscriptionRequest,
)
from .providers.paystack import PaystackProvider
from .providers.opay import OPayProvider
from .providers.stripe_provider import StripeProvider


router = APIRouter(prefix="/payments", tags=["payments"])
subscription_router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


# ==================== PAYMENT ENDPOINTS ====================

@router.post("/initialize", response_model=InitializePaymentResponse)
async def initialize_payment(
    request: InitializePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Initialize a payment for subscription upgrade.
    
    Returns an authorization URL to redirect the user to complete payment.
    """
    # Determine callback URL
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    callback_url = request.callback_url or f"{frontend_url}/subscribe/success"
    
    try:
        result = await payment_service.initialize_payment(
            user=current_user,
            plan=request.plan,
            billing_cycle=request.billing_cycle,
            provider=request.provider,
            callback_url=callback_url,
            db=db,
        )
        
        return InitializePaymentResponse(
            reference=result["reference"],
            authorization_url=result["authorization_url"],
            provider=result["provider"],
            amount=result["amount"],
            currency=result["currency"],
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/verify/{reference}", response_model=PaymentVerificationResponse)
async def verify_payment(
    reference: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Verify a payment status and activate subscription if successful.
    """
    try:
        result = await payment_service.verify_and_activate_subscription(
            reference=reference,
            db=db,
        )
        
        return PaymentVerificationResponse(
            reference=reference,
            status=result["status"],
            amount=result.get("amount", 0),
            currency="NGN",
            plan=result.get("plan"),
            billing_cycle=result.get("billing_cycle"),
            message=result["message"],
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ==================== WEBHOOK ENDPOINTS ====================

@router.post("/webhook/paystack")
async def paystack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle Paystack webhook notifications.
    
    Paystack sends charge.success events when a payment is successful.
    """
    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")
    
    # Verify signature
    provider = PaystackProvider()
    if not provider.verify_webhook_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )
    
    # Parse event
    import json
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )
    
    event_type = event.get("event")
    
    if event_type == "charge.success":
        data = event.get("data", {})
        reference = data.get("reference")
        
        if reference:
            try:
                await payment_service.verify_and_activate_subscription(
                    reference=reference,
                    db=db,
                )
            except ValueError:
                pass  # Transaction not found, ignore
    
    return {"status": "success"}


@router.post("/webhook/opay")
async def opay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle OPay webhook/callback notifications.
    """
    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("x-opay-signature", "")
    
    # Verify signature
    provider = OPayProvider()
    if signature and not provider.verify_webhook_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )
    
    # Parse event
    import json
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )
    
    # Extract reference from OPay callback
    reference = event.get("data", {}).get("reference") or event.get("reference")
    status_value = event.get("data", {}).get("status", "").lower()
    
    if reference and status_value == "success":
        try:
            await payment_service.verify_and_activate_subscription(
                reference=reference,
                db=db,
            )
        except ValueError:
            pass  # Transaction not found, ignore
    
    return {"status": "success"}


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle Stripe webhook notifications.
    
    Stripe sends checkout.session.completed events when payment succeeds.
    """
    import json
    
    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("stripe-signature", "")
    
    # Verify signature
    provider = StripeProvider()
    if not provider.verify_webhook_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )
    
    # Parse event
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )
    
    event_type = event.get("type")
    
    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        reference = session.get("client_reference_id") or session.get("metadata", {}).get("reference")
        
        if reference:
            try:
                await payment_service.verify_and_activate_subscription(
                    reference=reference,
                    db=db,
                )
            except ValueError:
                pass  # Transaction not found, ignore
    
    return {"status": "success"}


# ==================== SUBSCRIPTION ENDPOINTS ====================

@subscription_router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get the current user's active subscription.
    
    Creates a free subscription if none exists.
    """
    subscription = await payment_service.get_or_create_subscription(
        user=current_user,
        db=db,
    )
    
    return subscription


@subscription_router.post("/cancel")
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Cancel the current user's subscription.
    
    Access continues until the end of the current billing period.
    """
    try:
        result = await payment_service.cancel_subscription(
            user_id=current_user.id,
            reason=request.reason,
            db=db,
        )
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
