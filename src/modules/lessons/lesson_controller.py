# src/lessons/lesson_controller.py

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.common.utils.global_functions import award_xp
from src.modules.achievements.achievement_tasks import award_achievement
from src.modules.lessons import lesson_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user  # Assumes implementation exists
from src.models.models import User, UserLesson

router = APIRouter(prefix="/courses", tags=["lessons"])

# GET /courses/{course_id}/lessons - Retrieve lessons for a course
@router.get("/{course_id}/lessons", response_model=List[schemas.LessonResponse])
async def get_lessons(
    course_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    lessons = await lesson_service.get_lessons_by_course(course_id, db)
    if not lessons:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No lessons found for this course"
        )
    return lessons

# PUT /courses/{course_id}/lessons/{lesson_id}/complete - Mark a lesson as completed
@router.put("/{course_id}/lessons/{lesson_id}/complete", response_model=schemas.CompleteLessonResponse)
async def complete_lesson(
    course_id: str,
    lesson_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    success = await lesson_service.complete_lesson(course_id, lesson_id, current_user, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to mark lesson as completed (it may not exist, belong to the course, or has been already completed)"
        )
    
    await award_xp(current_user, db)
    
    # Query the number of completed lessons for the user
    result = await db.execute(select(UserLesson).where(UserLesson.user_id == current_user.id))
    completed_lessons = result.scalars().all()    
    # If this is the first completed lesson, schedule awarding the "First Step" achievement.
    if len(completed_lessons) == 1:
        background_tasks.add_task(award_achievement, str(current_user.id), "First Step")

    # Now, check if the user has completed all lessons in the course.
    # Get all lessons for the course.
    lessons = await lesson_service.get_lessons_by_course(course_id, db)
    total_lessons = len(lessons)
    # Extract the IDs of the lessons in this course.
    lesson_ids = [lesson.id for lesson in lessons]    
    # Query the number of lessons in this course that the user has completed.
    result = await db.execute(
        select(UserLesson).where(
            UserLesson.user_id == current_user.id,
            UserLesson.lesson_id.in_(lesson_ids)
        )
    )
    completed_lessons_in_course = result.scalars().all()    
    if total_lessons > 0 and len(completed_lessons_in_course) == total_lessons:
        background_tasks.add_task(award_achievement, str(current_user.id), "Subject Master")

    # Award "Quick Learner" if the user has completed 5 lessons in a single day.
    # Define today's time range (UTC)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    result = await db.execute(
        select(UserLesson).where(
            UserLesson.user_id == current_user.id,
            UserLesson.completed_at >= today_start,
            UserLesson.completed_at < today_end
        )
    )
    completed_lessons_today = result.scalars().all()
    if len(completed_lessons_today) == 5:
        background_tasks.add_task(award_achievement, str(current_user.id), "Quick Learner")

    return schemas.CompleteLessonResponse(message="Lesson marked as completed.")


@router.get("/{lesson_id}", response_model=schemas.LessonResponse)
async def get_lesson(
    lesson_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve the details of a specific lesson by its ID.
    """
    lesson = await lesson_service.get_lesson_by_id(lesson_id, db)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found."
        )
    return lesson