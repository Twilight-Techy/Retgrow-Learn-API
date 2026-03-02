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
        title = "🎉 Achievement Unlocked!"
        message = f"Amazing work! You've just earned the '{achievement_title}' achievement. Keep up the momentum! 🚀"
        
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
        title = f"Track Updates: {action.capitalize()}"
        
        if action == "added":
            message = f"🌟 New track alert! '{track_title}' is now available. Ready to dive in?"
        elif action == "updated":
            message = f"✨ '{track_title}' just got an update! Check out what's new."
        else:
            message = f"The track '{track_title}' has been removed."
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
        
        if action == "added":
            message = f"📚 Exciting news! A new course '{course_title}' has just been added to your track. Start learning today!"
        elif action == "updated":
            message = f"🔄 The course '{course_title}' has been updated with fresh content! Jump back in to see."
        else:
            message = f"The course '{course_title}' has been removed from your track."
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
        title = f"New {item_type} Available!" if action == "added" else f"{item_type} {action.capitalize()}"
        
        if action == "added":
            message = f"🎓 A new {item_type.lower()} '{item_title}' is ready for you! Let's get to work."
        elif action == "updated":
            message = f"✏️ Heads up! The {item_type.lower()} '{item_title}' was recently updated. Make sure you haven't missed anything."
        else:
            message = f"The {item_type.lower()} '{item_title}' has been removed from your course."
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
        title = f"New {item_type}!" if action == "added" else f"{item_type} {action.capitalize()}"
        if action == "added":
            message = f"📎 We've added a helpful new {item_type.lower()} '{item_title}' to your track. Check it out!"
        elif action == "updated":
            message = f"📝 The {item_type.lower()} '{item_title}' has been revised. Take a look at the latest version."
        else:
            message = f"The {item_type.lower()} '{item_title}' is no longer available."
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
