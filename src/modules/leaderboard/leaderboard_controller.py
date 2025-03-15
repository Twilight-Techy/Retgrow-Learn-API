# src/leaderboard/leaderboard_controller.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.modules.leaderboard import leaderboard_service, schemas
from src.common.database.database import get_db_session

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

@router.get("", response_model=List[schemas.LeaderboardEntry])
async def get_leaderboard(db: AsyncSession = Depends(get_db_session)):
    """
    Retrieve the top users leaderboard.
    """
    leaderboard = await leaderboard_service.get_leaderboard(db, limit=10)
    return leaderboard
