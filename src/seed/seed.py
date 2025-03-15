import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# Import the async_session from your database configuration.
from src.common.database.database import async_session
# Import your Achievement model.
from src.models.models import Achievement

# This is the seed data as defined in your mock.
achievements_data = [
    {"name": "First Step", "description": "Complete your first lesson"},
    {"name": "Quick Learner", "description": "Complete 5 lessons in a day"},
    {"name": "Consistent", "description": "Log in for 7 consecutive days"},
    {"name": "Subject Master", "description": "Complete all lessons in a course"},
    {"name": "Helper", "description": "Answer 10 questions in the forum"},
]

async def seed_achievements(session: AsyncSession):
    """
    Seed the achievements table with predefined achievement definitions.
    """
    # (Optional) Uncomment the next line if you want to clear existing achievements first.
    # await session.execute(delete(Achievement))
    for data in achievements_data:
        achievement = Achievement(
            title=data["name"],
            description=data["description"],
            # icon_url can be set here if needed, otherwise it remains None.
        )
        session.add(achievement)

async def seed_all():
    """
    Run all seed functions. You can add additional seed functions here.
    """
    async with async_session() as session:
        # Using a transaction block to ensure all seeding operations succeed.
        async with session.begin():
            await seed_achievements(session)
            # Call additional seed functions here (e.g., await seed_tracks(session), etc.)
        await session.commit()  # Commit the transaction

if __name__ == "__main__":
    asyncio.run(seed_all())
