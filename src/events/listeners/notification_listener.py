import logging
from sqlalchemy.ext.asyncio import AsyncSession
from src.events.dispatcher import dispatcher
from src.models.models import NotificationType
from src.modules.notifications.notification_service import create_notification

logger = logging.getLogger(__name__)

async def notify_achievement_unlocked(user_id: str, achievement_title: str, db: AsyncSession, **kwargs):
    """
    Listens for 'achievement_unlocked'.
    Creates a new Notification row to alert the user about their gamification award.
    """
    try:
        title = "Achievement Unlocked!"
        message = f"Congratulations! You've earned the '{achievement_title}' achievement."
        
        await create_notification(
            user_id=user_id,
            title=title,
            message=message,
            db=db,
            notif_type=NotificationType.SUCCESS,
            commit=False # The dispatcher will commit
        )
        logger.info(f"Notification queued for unlocked achievement '{achievement_title}' for user {user_id}")
    except Exception as e:
        logger.error(f"Error creating notification for achievement {achievement_title}: {e}")

# Subscribe listeners
dispatcher.subscribe("achievement_unlocked", notify_achievement_unlocked)
