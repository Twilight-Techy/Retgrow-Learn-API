import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.common.database.database import async_session
from src.models.models import UserAchievement, Achievement

async def _award_achievement(user_id: str, achievement_title: str, db: AsyncSession):
    # Find the achievement by title
    result = await db.execute(select(Achievement).where(Achievement.title == achievement_title))
    achievement = result.scalars().first()
    if not achievement:
        print(f"Achievement '{achievement_title}' not found.")
        return

    # Check if the user already has the achievement
    result = await db.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement.id
        )
    )
    if result.scalars().first():
        print(f"User {user_id} already has achievement '{achievement_title}'.")
        return

    # Award the achievement
    new_award = UserAchievement(user_id=user_id, achievement_id=achievement.id)
    db.add(new_award)
    await db.commit()
    print(f"Achievement '{achievement_title}' awarded to user {user_id}.")

async def award_achievement(user_id: str, achievement_title: str):
    """
    Schedules a background task to award an achievement to the user.
    This function is intended to be called from a FastAPI BackgroundTasks context.
    """
    async with async_session() as session:
        await _award_achievement(user_id, achievement_title, session)
