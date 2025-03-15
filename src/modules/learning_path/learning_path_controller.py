# src/learning_path/learning_path_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.modules.learning_path import learning_path_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user
from src.models.models import User

router = APIRouter(prefix="/user", tags=["learning-path"])

@router.get("/learning-path", response_model=schemas.LearningPathResponse)
async def get_learning_path(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve the learning path for the currently authenticated user.
    """
    learning_path = await learning_path_service.get_learning_path(str(current_user.id), db)
    if not learning_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning path not found for this user."
        )
    return learning_path

@router.get("/skills", response_model=List[schemas.UserSkillResponse])
async def get_user_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve all skills for the currently authenticated user.
    """
    user_skills = await learning_path_service.get_user_skills(str(current_user.id), db)
    if not user_skills:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No skills found for this user."
        )
    return user_skills

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