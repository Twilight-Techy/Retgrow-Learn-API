"""
Abstract base class for payment providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, Any

from src.models.models import PaymentProvider


@dataclass
class PaymentInitResult:
    """Result of initializing a payment."""
    success: bool
    authorization_url: Optional[str] = None
    external_reference: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class PaymentVerifyResult:
    """Result of verifying a payment."""
    success: bool
    status: str  # 'success', 'failed', 'pending'
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    external_reference: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class BasePaymentProvider(ABC):
    """Abstract base class for payment providers."""
    
    provider: PaymentProvider
    
    @abstractmethod
    async def initialize_payment(
        self,
        amount: Decimal,
        email: str,
        reference: str,
        callback_url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentInitResult:
        """
        Initialize a payment transaction.
        
        Args:
            amount: Amount in Naira
            email: Customer email
            reference: Our internal reference
            callback_url: URL to redirect after payment
            metadata: Additional metadata to store
            
        Returns:
            PaymentInitResult with authorization URL if successful
        """
        pass
    
    @abstractmethod
    async def verify_payment(self, reference: str) -> PaymentVerifyResult:
        """
        Verify a payment transaction status.
        
        Args:
            reference: Our internal reference or external reference
            
        Returns:
            PaymentVerifyResult with payment status
        """
        pass
    
    @abstractmethod
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verify webhook signature from payment provider.
        
        Args:
            payload: Raw request body
            signature: Signature from request headers
            
        Returns:
            True if signature is valid
        """
        pass
