"""
Subscription API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.database import get_db_session
from src.models.models import User
from src.auth.dependencies import get_current_user
from src.modules.payments.schemas import SubscriptionResponse, CancelSubscriptionRequest

from . import subscription_service

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get the current user's active subscription.
    
    Creates a free subscription if none exists.
    """
    subscription = await subscription_service.get_or_create_subscription(
        user=current_user,
        db=db,
    )
    
    return subscription


@router.post("/cancel")
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
        result = await subscription_service.cancel_subscription(
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
