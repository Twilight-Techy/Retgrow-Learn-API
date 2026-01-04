"""
Paystack payment provider implementation.
"""
import hmac
import hashlib
from decimal import Decimal
from typing import Optional, Dict, Any
import httpx

from src.models.models import PaymentProvider
from src.common.config import settings
from .base import BasePaymentProvider, PaymentInitResult, PaymentVerifyResult


class PaystackProvider(BasePaymentProvider):
    """Paystack payment provider implementation."""
    
    provider = PaymentProvider.PAYSTACK
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY
        self.base_url = "https://api.paystack.co"
        
    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.secret_key}",
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
        Initialize a Paystack transaction.
        
        Amount should be in Naira - will be converted to kobo.
        """
        # Convert Naira to kobo (multiply by 100)
        amount_kobo = int(amount * 100)
        
        payload = {
            "email": email,
            "amount": amount_kobo,
            "reference": reference,
            "callback_url": callback_url,
            "currency": "NGN",
        }
        
        if metadata:
            payload["metadata"] = metadata
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/transaction/initialize",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0,
                )
                
                data = response.json()
                
                if response.status_code == 200 and data.get("status"):
                    return PaymentInitResult(
                        success=True,
                        authorization_url=data["data"]["authorization_url"],
                        external_reference=data["data"]["reference"],
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
        """Verify a Paystack transaction."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/transaction/verify/{reference}",
                    headers=self.headers,
                    timeout=30.0,
                )
                
                data = response.json()
                
                if response.status_code == 200 and data.get("status"):
                    tx_data = data["data"]
                    status = tx_data.get("status", "").lower()
                    
                    # Convert kobo back to Naira
                    amount_kobo = tx_data.get("amount", 0)
                    amount_naira = Decimal(amount_kobo) / 100
                    
                    return PaymentVerifyResult(
                        success=status == "success",
                        status=status,
                        amount=amount_naira,
                        currency=tx_data.get("currency", "NGN"),
                        external_reference=tx_data.get("reference"),
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
        Verify Paystack webhook signature.
        
        Paystack uses HMAC SHA512 with the secret key.
        Signature is passed in 'x-paystack-signature' header.
        """
        if not self.secret_key:
            return False
            
        expected_signature = hmac.new(
            self.secret_key.encode("utf-8"),
            payload,
            hashlib.sha512,
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
