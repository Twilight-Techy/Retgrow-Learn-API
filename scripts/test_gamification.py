import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())

import logging
from src.common.database.database import async_session
from sqlalchemy.future import select

# We must import the main module to ensure listeners are registered
# (Moved into the try block to catch ImportErrors)

logging.basicConfig(level=logging.INFO, filename="test_success.log", filemode="w")
logger = logging.getLogger(__name__)

async def test_gamification():
    async with async_session() as session:
        # Find a user to test with
        user_res = await session.execute(select(User).limit(1))
        user = user_res.scalars().first()
        if not user:
            logger.error("No user found to test with.")
            return

        user_id = str(user.id)
        logger.info(f"Testing gamification events with user: {user.email}")

        # 0. Seed the achievement if it doesn't exist
        ach_res = await session.execute(select(Achievement).where(Achievement.title == "Track Master"))
        track_ach = ach_res.scalars().first()
        if not track_ach:
            logger.info("Seeding 'Track Master' achievement...")
            track_ach = Achievement(title="Track Master", description="Complete an entire learning path", icon_url="")
            session.add(track_ach)
            await session.commit()
            await session.refresh(track_ach)

        # 0.5 Clean up any existing UserAchievements for Track Master for this user so we can test the trigger again
        # Also clean up existing notifications so we start fresh
        if track_ach:
            await session.execute(
                UserAchievement.__table__.delete().where(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == track_ach.id
                )
            )
            await session.execute(
                Notification.__table__.delete().where(
                    Notification.user_id == user_id,
                    Notification.title == "Achievement Unlocked!"
                )
            )
            await session.commit()

        # 1. Dispatch a track completion event
        logger.info("--- Dispatching track_completed event ---")
        await dispatcher.dispatch("track_completed", user_id=user_id, track_id="some_uuid_here")

        # Sleep briefly to ensure background tasks complete
        await asyncio.sleep(2)

        # 2. Check if the user received the 'Track Master' achievement
        ach_res = await session.execute(select(Achievement).where(Achievement.title == "Track Master"))
        track_ach = ach_res.scalars().first()

        if track_ach:
            user_ach_res = await session.execute(
                select(UserAchievement).where(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == track_ach.id
                )
            )
            has_ach = user_ach_res.scalars().first()
            if has_ach:
                logger.info("SUCCESS: User was successfully awarded 'Track Master' via the event system!")
            else:
                logger.error("FAILED: 'Track Master' was not awarded to the user.")
        else:
            logger.warning("FAILED: 'Track Master' achievement title does not exist in DB yet to test against. We might need to seed it.")

        # 3. Check if a notification was sent for the achievement
        notif_res = await session.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.title == "Achievement Unlocked!"
            )
        )
        notifs = notif_res.scalars().all()
        if notifs:
            logger.info(f"SUCCESS: Notification trigger worked! Found {len(notifs)} matching notifications for this user.")
        else:
            logger.error("FAILED: No target notifications found.")

if __name__ == "__main__":
    try:
        import src.main
        from src.events.dispatcher import dispatcher
        from src.models.models import User, Notification, UserAchievement, Achievement
        asyncio.run(test_gamification())
    except Exception as e:
        import traceback
        with open("error_trace.txt", "w") as f:
            f.write(traceback.format_exc())
