# src/lessons/lesson_controller.py

from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.common.utils.global_functions import award_xp, ensure_instructor_or_admin
from src.modules.achievements.achievement_tasks import award_achievement
from src.modules.lessons import lesson_service, schemas
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user
from src.models.models import User, UserLesson

router = APIRouter(prefix="/courses", tags=["lessons"])

# GET /courses/{course_id}/lessons - Retrieve lessons for a course
@router.get("/{course_id}/lessons", response_model=List[schemas.LessonResponse])
async def get_lessons(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve all lessons for a course.
    """
    lessons = await lesson_service.get_lessons_by_course(str(course_id), str(current_user.id), db)
    if not lessons:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No lessons found for this course"
        )
    return lessons

# PUT /courses/{course_id}/lessons/{lesson_id}/complete - Mark a lesson as completed
@router.put("/{course_id}/lessons/{lesson_id}/complete", response_model=schemas.CompleteLessonResponse)
async def complete_lesson(
    course_id: UUID,
    lesson_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Mark a lesson as completed within a course context.
    """
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
    lessons = await lesson_service.get_lessons_by_course(str(course_id), str(current_user.id), db)
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


# GET /courses/{course_id}/lessons/{lesson_id} - fetch single lesson (requires enrollment)
@router.get("/{course_id}/lessons/{lesson_id}", response_model=schemas.LessonResponse)
async def get_lesson(
    course_id: UUID,
    lesson_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieve the details of a specific lesson in a course.
    Requires the requesting user to be enrolled in the course.
    """
    # verify enrollment
    enrolled = await lesson_service.is_user_enrolled_in_course(str(current_user.id), str(course_id), db)
    if not enrolled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be enrolled in this course to access the lesson")
    
    # verify lesson exists and belongs to course
    lesson = await lesson_service.get_lesson_in_course(str(course_id), str(lesson_id), db)
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    # Optionally: mark as completed automatically when retrieved by the user.
    # If you want "selection marks completion", call complete_lesson here (non-blocking).
    success = await lesson_service.complete_lesson(str(course_id), str(lesson_id), current_user, db)
    # success True/False is not used for response body, just side-effect.

    return lesson

@router.post("/module/{module_id}", response_model=schemas.LessonResponse)
async def create_lesson(
    module_id: UUID,
    lesson_data: schemas.LessonCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new lesson in a specific module.
    Only instructors and admins can create lessons.
    """
    ensure_instructor_or_admin(current_user)
    lesson = await lesson_service.create_lesson(str(module_id), lesson_data.model_dump(), db)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create lesson"
        )
    return lesson

@router.put("/{lesson_id}", response_model=schemas.LessonResponse)
async def update_lesson(
    lesson_id: UUID,
    lesson_data: schemas.LessonUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update an existing lesson.
    Only instructors and admins can update lessons.
    """
    ensure_instructor_or_admin(current_user)
    updated_lesson = await lesson_service.update_lesson(str(lesson_id), lesson_data.model_dump(), db)
    if not updated_lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    return updated_lesson

@router.get("/{course_id}/last-lesson", response_model=schemas.LastLessonResponse)
async def get_last_lesson_for_user(
    course_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Return the last completed lesson id for the current user in this course.
    If the user hasn't completed any lesson return the first lesson id of the course.
    Requires the user to be enrolled in the course (401/403 if not).
    """
    try:
        res = await lesson_service.get_last_or_first_lesson_for_user(str(course_id), str(current_user.id), db)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not enrolled in this course.")
    if res is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No lessons found for this course.")
    return res