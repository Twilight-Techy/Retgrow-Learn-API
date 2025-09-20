# src/achievements/achievement_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.modules.achievements import achievement_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user  # Ensure this is implemented
from src.models.models import User

router = APIRouter(prefix="/user", tags=["achievements"])

@router.get("/achievements", response_model=List[schemas.UserAchievementResponse])
async def get_user_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve all achievements earned by the currently authenticated user.
    """
    achievements = await achievement_service.get_user_achievements(str(current_user.id), db)
    return achievements

@router.get("/level", response_model=schemas.LevelResponse)
async def get_level_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Returns the current user's level progress.
    It uses the user's total XP (assumed to be stored in current_user.xp)
    to calculate the current level and the XP threshold for the next level.
    """
    # Make sure your User model has a field (e.g. `xp`) that stores the user's experience points.
    xp = getattr(current_user, "xp", 0)  # Default to 0 if not defined
    level_data = achievement_service.calculate_level_progress(xp)
    return level_data
