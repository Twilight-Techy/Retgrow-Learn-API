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
    result = await db.execute(select(User).order_by(User.xp.desc()).limit(limit))
    users = result.scalars().all()
    
    leaderboard = []
    for index, user in enumerate(users, start=1):
        # Build a display name. Use first and last name if available, otherwise use username.
        if user.first_name and user.last_name:
            display_name = f"{user.first_name} {user.last_name}"
        else:
            display_name = user.username
        # Use the user's avatar if available; otherwise, use a default placeholder.
        avatar = user.avatar_url if user.avatar_url else "/placeholder.svg?height=40&width=40"
        
        leaderboard.append({
            "rank": index,
            "name": display_name,
            "xp": user.xp,
            "avatar": avatar
        })
    
    return leaderboard
