# src/user/user_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user import user_service, schemas
from src.common.database.database import get_db_session
from src.models.models import User
from src.auth.dependencies import get_current_user  # Assumed to be implemented

router = APIRouter(prefix="/user", tags=["user"])

@router.get("/profile", response_model=schemas.ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve the profile for the currently authenticated user.
    """
    # Optionally, you could re-fetch the user from the DB here using the session if needed.
    # profile = await user_service.get_user_profile(current_user)
    # if not profile:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail="User profile not found"
    #     )
    # return profile
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    return current_user

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