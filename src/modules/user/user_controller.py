# src/user/user_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user import user_service, schemas
from src.common.database.database import get_db_session
from src.models.models import User
from src.auth.dependencies import get_current_user
from src.modules.subscriptions import subscription_service

router = APIRouter(prefix="/user", tags=["user"])

@router.get("/profile", response_model=schemas.ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve the profile for the currently authenticated user.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    # Get active subscription
    subscription = await subscription_service.get_active_subscription(current_user.id, db)
    
    # Create response with subscription details
    response = schemas.ProfileResponse.model_validate(current_user)
    if subscription:
        response.current_plan = subscription.plan.value
        response.subscription_status = subscription.status.value
    else:
        # Default to FREE if no specific subscription record found (though get_active usually returns one or None)
        # If user has no subscription record, they are effectively on FREE plan or NONE
        response.current_plan = "free" 
        response.subscription_status = "active"
        
    return response

@router.put("/profile", response_model=schemas.ProfileResponse)
async def update_profile(
    profile_data: schemas.UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update the profile of the currently authenticated user.
    
    Only the provided fields will be updated.
    """
    updated_user = await user_service.update_user_profile(current_user, profile_data.model_dump(), db)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    return updated_user

@router.get("/progress", response_model=schemas.UserProgressResponse)
async def get_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve the progress for the currently authenticated user.
    
    The response includes:
      - overall_progress: The average progress across enrolled courses.
      - courses: A list of courses with individual progress values.
    """
    progress = await user_service.get_user_progress(current_user, db)
    return progress