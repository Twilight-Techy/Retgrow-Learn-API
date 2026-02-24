# src/lessons/lesson_controller.py

from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.common.utils.global_functions import award_xp, ensure_instructor_or_admin
from src.events.dispatcher import dispatcher
from src.modules.lessons import lesson_service, schemas
from src.common.database.database import get_db_session
from src.common.database.database import get_db_session
from src.auth.dependencies import get_current_user
from src.models.models import User, UserLesson, Module, Lesson

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
    lessons = await lesson_service.get_lessons_by_course(str(course_id), current_user, db)
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
    
    
    # Broadcast event for module completion
    background_tasks.add_task(dispatcher.dispatch, "module_completed", user_id=str(current_user.id), module_id=str(lesson_id))

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
    try:
        lesson = await lesson_service.get_lesson_in_course(str(course_id), str(lesson_id), db, current_user)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    # Optionally: mark as completed automatically when retrieved by the user.
    # If you want "selection marks completion", call complete_lesson here (non-blocking).
    if lesson.content: # Only mark complete if they actually accessed the content (not just metadata)
        success = await lesson_service.complete_lesson(str(course_id), str(lesson_id), current_user, db)
    # success True/False is not used for response body, just side-effect.

    return lesson

async def dispatch_lesson_event(lesson: Lesson, action: str, db: AsyncSession, background_tasks: BackgroundTasks):
    try:
        # Need to find the associated course_id by traversing up to the Module
        stmt = select(Module.course_id).where(Module.id == lesson.module_id)
        result = await db.execute(stmt)
        course_id = result.scalars().first()
        if course_id:
            background_tasks.add_task(dispatcher.dispatch, "course_content_event", item_type="Lesson", item_title=lesson.title, course_id=str(course_id), action=action)
    except Exception as e:
        import logging
        logging.error(f"Failed to dispatch lesson event: {e}")

@router.post("/module/{module_id}", response_model=schemas.LessonResponse)
async def create_lesson(
    module_id: UUID,
    lesson_data: schemas.LessonCreateRequest,
    background_tasks: BackgroundTasks,
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
    await dispatch_lesson_event(lesson, "added", db, background_tasks)
    return lesson

@router.put("/{lesson_id}", response_model=schemas.LessonResponse)
async def update_lesson(
    lesson_id: UUID,
    lesson_data: schemas.LessonUpdateRequest,
    background_tasks: BackgroundTasks,
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
    await dispatch_lesson_event(updated_lesson, "updated", db, background_tasks)
    return updated_lesson

@router.delete("/{lesson_id}", response_model=dict)
async def delete_lesson(
    lesson_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete an existing lesson.
    Only instructors and admins can delete lessons.
    """
    ensure_instructor_or_admin(current_user)
    
    # Needs lesson instance to dispatch event before deletion
    stmt = select(Lesson).where(Lesson.id == lesson_id)
    result = await db.execute(stmt)
    lesson_to_delete = result.scalars().first()
    
    if not lesson_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found."
        )

    # Re-use your service delete function
    await lesson_service.delete_lesson(str(lesson_id), db)  # Assuming lesson_service has this method
    
    await dispatch_lesson_event(lesson_to_delete, "deleted", db, background_tasks)
    return {"message": "Lesson deleted successfully"}

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