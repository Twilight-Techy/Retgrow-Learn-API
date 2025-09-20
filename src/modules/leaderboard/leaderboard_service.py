# src/leaderboard/leaderboard_service.py

from typing import List
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.models import User  # Adjust the import path based on your project structure

async def get_leaderboard(db: AsyncSession, limit: int = 10) -> List[dict]:
    """
    Query the database for the top users by XP and return leaderboard data.
    """
    # Query the users ordered by XP in descending order.
    stmt = select(User).order_by(User.xp.desc()).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()
