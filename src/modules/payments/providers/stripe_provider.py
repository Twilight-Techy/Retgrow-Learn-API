"""
Stripe payment provider implementation.
"""
from decimal import Decimal
from typing import Optional, Dict, Any

import stripe

from src.models.models import PaymentProvider
from src.common.config import settings
from .base import BasePaymentProvider, PaymentInitResult, PaymentVerifyResult


class StripeProvider(BasePaymentProvider):
    """Stripe Checkout payment provider implementation."""
    
    provider = PaymentProvider.STRIPE
    
    def __init__(self):
        self.secret_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        
        # Configure stripe with the secret key
        stripe.api_key = self.secret_key
    
    async def initialize_payment(
        self,
        amount: Decimal,
        email: str,
        reference: str,
        callback_url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentInitResult:
        """
        Initialize a Stripe Checkout Session.
        
        Amount should be in Naira - will be converted to smallest unit (kobo equivalent).
        """
        # Convert Naira to smallest currency unit (kobo = Naira * 100)
        amount_smallest = int(amount * 100)
        
        # Extract plan info from metadata
        plan_name = metadata.get("plan", "Subscription") if metadata else "Subscription"
        billing_cycle = metadata.get("billing_cycle", "monthly") if metadata else "monthly"
        
        try:
            # Determine cancel URL
            cancel_url = callback_url.replace("/success", "/cancel") if "/success" in callback_url else callback_url
            
            # Create Stripe Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="payment",  # One-time payment for subscription period
                customer_email=email,
                client_reference_id=reference,
                line_items=[
                    {
                        "price_data": {
                            "currency": "ngn",
                            "unit_amount": amount_smallest,
                            "product_data": {
                                "name": f"Retgrow Learn - {plan_name.title()} ({billing_cycle.title()})",
                                "description": f"Subscription to Retgrow Learn platform",
                            },
                        },
                        "quantity": 1,
                    }
                ],
                success_url=f"{callback_url}?reference={reference}&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url,
                metadata={
                    "reference": reference,
                    "plan": plan_name,
                    "billing_cycle": billing_cycle,
                    **(metadata or {}),
                },
            )
            
            return PaymentInitResult(
                success=True,
                authorization_url=session.url,
                external_reference=session.id,
            )
            
        except stripe.error.StripeError as e:
            return PaymentInitResult(
                success=False,
                error_message=str(e.user_message if hasattr(e, 'user_message') else e),
            )
        except Exception as e:
            return PaymentInitResult(
                success=False,
                error_message=str(e),
            )
    
    async def verify_payment(self, reference: str) -> PaymentVerifyResult:
        """
        Verify a Stripe payment by retrieving the checkout session.
        
        Reference can be either our internal reference (client_reference_id) or 
        the Stripe session ID.
        """
        try:
            # First try to retrieve as session ID
            if reference.startswith("cs_"):
                session = stripe.checkout.Session.retrieve(reference)
            else:
                # Search for session by client_reference_id
                sessions = stripe.checkout.Session.list(
                    limit=1,
                )
                # Filter by reference in metadata
                session = None
                for s in sessions.data:
                    if s.client_reference_id == reference or s.metadata.get("reference") == reference:
                        session = s
                        break
                
                if not session:
                    return PaymentVerifyResult(
                        success=False,
                        status="not_found",
                        error_message=f"Session not found for reference: {reference}",
                    )
            
            # Check payment status
            if session.payment_status == "paid":
                # Convert from smallest unit back to Naira
                amount_smallest = session.amount_total or 0
                amount_naira = Decimal(amount_smallest) / 100
                
                return PaymentVerifyResult(
                    success=True,
                    status="success",
                    amount=amount_naira,
                    currency=session.currency.upper() if session.currency else "NGN",
                    external_reference=session.id,
                    raw_response={"session_id": session.id, "payment_status": session.payment_status},
                )
            elif session.payment_status == "unpaid":
                return PaymentVerifyResult(
                    success=False,
                    status="pending",
                    error_message="Payment not yet completed",
                )
            else:
                return PaymentVerifyResult(
                    success=False,
                    status="failed",
                    error_message=f"Payment status: {session.payment_status}",
                )
                
        except stripe.error.StripeError as e:
            return PaymentVerifyResult(
                success=False,
                status="error",
                error_message=str(e.user_message if hasattr(e, 'user_message') else e),
            )
        except Exception as e:
            return PaymentVerifyResult(
                success=False,
                status="error",
                error_message=str(e),
            )
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verify Stripe webhook signature.
        
        Stripe uses the Stripe-Signature header with HMAC SHA256.
        """
        if not self.webhook_secret:
            return False
            
        try:
            # This will raise an exception if verification fails
            stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret,
            )
            return True
        except (stripe.error.SignatureVerificationError, ValueError):
            return False
