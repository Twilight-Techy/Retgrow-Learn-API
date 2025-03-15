# src/lessons/lesson_service.py

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from src.models.models import Lesson, Module, UserLesson, User

async def get_lessons_by_course(course_id: str, db: AsyncSession) -> List[Lesson]:
    """
    Retrieve all lessons for a given course.
    
    This query joins the Lesson and Module tables and filters by course_id.
    """
    # Assuming each Lesson belongs to a Module and Module has a course_id field.
    stmt = (
        select(Lesson)
        .join(Module)
        .where(Module.course_id == course_id)
        .order_by(Lesson.order)
    )
    result = await db.execute(stmt)
    lessons = result.scalars().all()
    return lessons

async def complete_lesson(course_id: str, lesson_id: str, current_user: User, db: AsyncSession) -> bool:
    """
    Mark a lesson as completed for the current user.
    
    First, verify that the lesson exists and belongs to the given course.
    Then check if a completion record already exists in the UserLesson table.
    If not, create a new record.
    """
    # Verify that the lesson exists and is part of a module within the given course.
    stmt = (
        select(Lesson)
        .join(Module)
        .where(
            and_(
                Lesson.id == lesson_id,
                Module.course_id == course_id
            )
        )
    )
    result = await db.execute(stmt)
    lesson = result.scalars().first()
    if not lesson:
        return False  # Lesson not found or does not belong to the course

    # Check if the user has already completed the lesson.
    stmt = select(UserLesson).where(
        and_(
            UserLesson.user_id == current_user.id,
            UserLesson.lesson_id == lesson_id
        )
    )
    result = await db.execute(stmt)
    existing_record = result.scalars().first()
    if existing_record:
        return False  # Already marked as completed

    # Create a new UserLesson record.
    new_completion = UserLesson(
        user_id=current_user.id,
        lesson_id=lesson_id
    )
    db.add(new_completion)
    await db.commit()
    return True

async def get_lesson_by_id(lesson_id: str, db: AsyncSession) -> Optional[Lesson]:
    stmt = select(Lesson).where(Lesson.id == lesson_id)
    result = await db.execute(stmt)
    lesson = result.scalars().first()
    return lesson