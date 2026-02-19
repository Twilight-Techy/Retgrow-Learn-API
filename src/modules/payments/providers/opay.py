"""
OPay Express Checkout payment provider implementation.
"""
import hmac
import hashlib
from decimal import Decimal
from typing import Optional, Dict, Any
import httpx

from src.models.models import PaymentProvider
from src.common.config import settings
from .base import BasePaymentProvider, PaymentInitResult, PaymentVerifyResult


class OPayProvider(BasePaymentProvider):
    """OPay Express Checkout (Cashier) payment provider implementation."""
    
    provider = PaymentProvider.OPAY
    
    def __init__(self):
        self.public_key = settings.OPAY_PUBLIC_KEY
        self.secret_key = settings.OPAY_SECRET_KEY
        self.merchant_id = settings.OPAY_MERCHANT_ID
        self.environment = settings.OPAY_ENVIRONMENT
        
        # Set base URL based on environment
        if self.environment == "production":
            self.base_url = "https://api.opaycheckout.com"
        else:
            self.base_url = "https://sandboxapi.opaycheckout.com"
    
    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.public_key}",
            "MerchantId": self.merchant_id,
            "Content-Type": "application/json",
        }
    
    async def initialize_payment(
        self,
        amount: Decimal,
        email: str,
        reference: str,
        callback_url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentInitResult:
        """
        Initialize an OPay Cashier payment.
        
        Amount should be in Naira - OPay uses cent units (kobo).
        """
        # Convert Naira to kobo (cent units)
        amount_kobo = int(amount * 100)
        
        # Extract user info from metadata if available
        user_info = metadata.get("user_info", {}) if metadata else {}
        
        payload = {
            "country": "NG",  # Nigeria
            "reference": reference,
            "amount": {
                "total": amount_kobo,
                "currency": "NGN",
            },
            "returnUrl": callback_url,
            "callbackUrl": callback_url,  # Will be overridden by webhook URL
            "cancelUrl": callback_url.replace("/success", "/cancel") if "/success" in callback_url else callback_url,
            "expireAt": 1800,  # 30 minutes
            "userInfo": {
                "userEmail": email,
                "userId": user_info.get("user_id", ""),
                "userName": user_info.get("user_name", email.split("@")[0]),
            },
            "productList": [
                {
                    "productId": metadata.get("plan", "subscription") if metadata else "subscription",
                    "name": f"Retgrow Learn {metadata.get('plan', 'Subscription')}" if metadata else "Subscription",
                    "description": f"Subscription to Retgrow Learn - {metadata.get('billing_cycle', 'monthly')}" if metadata else "Subscription",
                    "price": amount_kobo,
                    "quantity": 1,
                }
            ],
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/international/cashier/create",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0,
                )
                
                data = response.json()
                
                # OPay returns code "00000" for success
                if data.get("code") == "00000":
                    return PaymentInitResult(
                        success=True,
                        authorization_url=data["data"]["cashierUrl"],
                        external_reference=data["data"]["orderNo"],
                    )
                else:
                    return PaymentInitResult(
                        success=False,
                        error_message=data.get("message", "Failed to initialize payment"),
                    )
                    
        except Exception as e:
            return PaymentInitResult(
                success=False,
                error_message=str(e),
            )
    
    async def verify_payment(self, reference: str) -> PaymentVerifyResult:
        """
        Query OPay payment status.
        
        Uses the order query endpoint.
        """
        payload = {
            "country": "NG",
            "reference": reference,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/international/cashier/status",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0,
                )
                
                data = response.json()
                
                if data.get("code") == "00000":
                    tx_data = data.get("data", {})
                    status = tx_data.get("status", "").lower()
                    
                    # Map OPay status to our status
                    status_map = {
                        "success": "success",
                        "pending": "pending",
                        "fail": "failed",
                        "close": "cancelled",
                    }
                    normalized_status = status_map.get(status, "pending")
                    
                    # Convert kobo back to Naira
                    amount_data = tx_data.get("amount", {})
                    amount_kobo = amount_data.get("total", 0)
                    amount_naira = Decimal(amount_kobo) / 100
                    
                    return PaymentVerifyResult(
                        success=normalized_status == "success",
                        status=normalized_status,
                        amount=amount_naira,
                        currency=amount_data.get("currency", "NGN"),
                        external_reference=tx_data.get("orderNo"),
                        raw_response=data,
                    )
                else:
                    return PaymentVerifyResult(
                        success=False,
                        status="failed",
                        error_message=data.get("message", "Verification failed"),
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
        Verify OPay webhook signature.
        
        OPay uses HMAC SHA512 with the secret key.
        """
        if not self.secret_key:
            return False
            
        expected_signature = hmac.new(
            self.secret_key.encode("utf-8"),
            payload,
            hashlib.sha512,
        ).hexdigest()
        
        return hmac.compare_digest(signature.lower(), expected_signature.lower())

    async def charge_subscription(
        self,
        amount: Decimal,
        email: str,
        authorization_code: str,
        reference: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentInitResult:
        """
        Charge user's saved card (Recurring).
        
        Not yet implemented for OPay.
        """
        return PaymentInitResult(
            success=False,
            error_message="Recurring payment is not yet supported for OPay provider."
        )
