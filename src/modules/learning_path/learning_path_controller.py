# src/learning_path/learning_path_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.modules.learning_path import learning_path_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user
from src.models.models import User

router = APIRouter(prefix="/user", tags=["learning-path"])

@router.get("/skills", response_model=List[schemas.UserSkillResponse])
async def get_user_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieve all user skills (skill object + proficiency + last_updated).
    Returns an empty list if the user has no skills.
    """
    # Check eligibility via access_control_service
    from src.modules.subscriptions import access_control_service
    if not await access_control_service.check_skills_access(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Skills tracking is available for Focused and Pro users only."
        )

    user_skills = await learning_path_service.get_user_skills(str(current_user.id), db)
    # Ensure it's a list (service should return list already)
    return user_skills or []

@router.post("/enroll", response_model=schemas.LearningPathResponse)
async def enroll_in_track(
    enroll_request: schemas.LearningPathEnrollRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Enroll the current user in a new track.
    If the user is already enrolled in a track that is not completed,
    that enrollment will be replaced by the new one.
    """
    new_learning_path = await learning_path_service.enroll_in_track(
        str(current_user.id),
        enroll_request.track_id,
        db
    )
    if not new_learning_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enrollment failed."
        )
    return new_learning_path