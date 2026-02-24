import logging
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.events.dispatcher import dispatcher
from src.models.models import UserLesson, UserCourse, LearningPath
from src.modules.achievements.achievement_tasks import _award_achievement

logger = logging.getLogger(__name__)

async def check_module_achievements(user_id: str, db: AsyncSession, **kwargs):
    """
    Listens for 'module_completed'.
    Awards 'First Steps' if this is the user's very first completed module.
    """
    try:
        # Check total modules completed by user
        res = await db.execute(
            select(func.count(UserLesson.id)).where(UserLesson.user_id == user_id, UserLesson.completed_at != None)
        )
        total_completed = res.scalar()
        
        if total_completed == 1:
            await _award_achievement(user_id, "First Steps", db)
            
    except Exception as e:
        logger.error(f"Error checking module achievements for {user_id}: {e}")

async def check_course_achievements(user_id: str, course_id: str, db: AsyncSession, **kwargs):
    """
    Listens for 'course_completed' or 'course_enrollment'.
    """
    try:
        # If it's a completion event, award Course Champion
        if kwargs.get("is_completion", False):
            await _award_achievement(user_id, "Course Champion", db)

        # Let's check enrollments for Knowledge Seeker
        res = await db.execute(
            select(func.count(UserCourse.user_id)).where(UserCourse.user_id == user_id)
        )
        total_enrolled = res.scalar()
        if total_enrolled >= 5:
            await _award_achievement(user_id, "Knowledge Seeker", db)

    except Exception as e:
        logger.error(f"Error checking course achievements for {user_id}: {e}")
        
async def check_track_achievements(user_id: str, track_id: str, db: AsyncSession, **kwargs):
    """
    Listens for 'track_completed'.
    """
    try:
        await _award_achievement(user_id, "Track Master", db)
    except Exception as e:
        logger.error(f"Error checking track achievements for {user_id}: {e}")

# Subscribe listeners
dispatcher.subscribe("module_completed", check_module_achievements)
dispatcher.subscribe("course_completed", check_course_achievements)
dispatcher.subscribe("course_enrolled", check_course_achievements)
dispatcher.subscribe("track_completed", check_track_achievements)
