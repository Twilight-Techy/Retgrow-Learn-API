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

# Subscription rules
dispatcher.subscribe("achievement_unlocked", notify_achievement_unlocked)

# --- Content Lifecycle Listeners ---

async def notify_track_event(track_title: str, action: str, db: AsyncSession, **kwargs):
    """
    Global notification: track created, updated, or deleted.
    action: "added", "updated", "deleted"
    """
    try:
        title = f"Track {action.capitalize()}"
        message = f"The track '{track_title}' has been {action}."
        await create_notification(
            title=title,
            message=message,
            db=db,
            notif_type=NotificationType.INFO,
            commit=False
        )
        logger.info(f"Notification queued for global track event: {title}")
    except Exception as e:
        logger.error(f"Error creating track notification: {e}")

async def notify_course_event(course_title: str, track_id: str, action: str, db: AsyncSession, **kwargs):
    """
    Scoped notification (track_id): course created, updated, or deleted.
    action: "added", "updated", "deleted"
    """
    try:
        title = f"Course {action.capitalize()}"
        message = f"The course '{course_title}' has been {action}."
        if track_id:
            await create_notification(
                title=title,
                message=message,
                db=db,
                track_id=track_id,
                notif_type=NotificationType.INFO,
                commit=False
            )
        logger.info(f"Notification queued for course event scoped to track {track_id}: {title}")
    except Exception as e:
        logger.error(f"Error creating course notification: {e}")

async def notify_course_content_event(item_type: str, item_title: str, course_id: str, action: str, db: AsyncSession, **kwargs):
    """
    Scoped notification (course_id): Module, Lesson, Quiz created, updated, or deleted.
    item_type: "Module", "Lesson", "Quiz"
    action: "added", "updated", "deleted"
    """
    try:
        title = f"{item_type} {action.capitalize()}"
        message = f"The {item_type.lower()} '{item_title}' has been {action}."
        if course_id:
            await create_notification(
                title=title,
                message=message,
                db=db,
                course_id=course_id,
                notif_type=NotificationType.INFO,
                commit=False
            )
        logger.info(f"Notification queued for {item_type} event scoped to course {course_id}: {title}")
    except Exception as e:
        logger.error(f"Error creating {item_type} notification: {e}")

async def notify_track_content_event(item_type: str, item_title: str, track_id: str, action: str, db: AsyncSession, **kwargs):
    """
    Scoped notification (track_id): Resource created, updated, or deleted.
    item_type: "Resource"
    action: "added", "updated", "deleted"
    """
    try:
        title = f"{item_type} {action.capitalize()}"
        message = f"The {item_type.lower()} '{item_title}' has been {action}."
        if track_id:
            await create_notification(
                title=title,
                message=message,
                db=db,
                track_id=track_id,
                notif_type=NotificationType.INFO,
                commit=False
            )
        logger.info(f"Notification queued for {item_type} event scoped to track {track_id}: {title}")
    except Exception as e:
        logger.error(f"Error creating {item_type} notification: {e}")

dispatcher.subscribe("track_event", notify_track_event)
dispatcher.subscribe("course_event", notify_course_event)
dispatcher.subscribe("course_content_event", notify_course_content_event)
dispatcher.subscribe("track_content_event", notify_track_content_event)
