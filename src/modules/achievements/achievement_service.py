# src/achievements/achievement_service.py

from typing import List
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.models import UserAchievement

async def get_user_achievements(user_id: str, db: AsyncSession) -> List[UserAchievement]:
    """
    Retrieve all achievements earned by the user.
    """
    result = await db.execute(select(UserAchievement).where(UserAchievement.user_id == user_id))
    achievements = result.scalars().all()
    return achievements

def calculate_level_progress(xp: int) -> dict:
    """
    Calculate the user's level based on their total XP.
    In this simple example, every 500 XP increases the level by 1.
    
    Args:
        xp (int): The total experience points of the user.
    
    Returns:
        dict: A dictionary with keys 'level', 'xp', and 'nextLevelXp'.
    """
    level = xp // 500  # Each level requires 500 XP.
    level += 1
    next_level_xp = (level + 1) * 500
    return {"level": level, "xp": xp, "nextLevelXp": next_level_xp}