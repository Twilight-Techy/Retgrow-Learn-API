# src/courses/course_service.py

from datetime import datetime, timezone 
from typing import List, Optional
from sqlalchemy import or_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import selectinload
from src.models.models import Course, Module, UserCourse, User
from src.modules.notifications.notification_service import create_notification

# Retrieve all courses
async def get_all_courses(db: AsyncSession, q: Optional[str] = None, skip: int = 0, limit: int = 10) -> List[Course]:
    """
    Retrieve courses from the database with optional search and pagination.
    
    Args:
        db (AsyncSession): The database session.
        q (Optional[str]): Optional search query to filter by title or description.
        skip (int): Number of records to skip (for pagination).
        limit (int): Maximum number of records to return.
        
    Returns:
        List[Course]: A list of courses matching the criteria.
    """
    if q:
        query = select(Course).where(
            or_(
                Course.title.ilike(f"%{q}%"),
                Course.description.ilike(f"%{q}%")
            )
        ).offset(skip).limit(limit)
    else:
        query = select(Course).offset(skip).limit(limit)
    
    result = await db.execute(query)
    courses = result.scalars().all()
    return courses

# Retrieve a single course by ID
async def get_course_by_id(course_id: str, db: AsyncSession) -> Optional[Course]:
    stmt = select(Course).where(Course.id == course_id)
    result = await db.execute(stmt)
    course = result.scalars().first()
    return course

async def create_course(course_data: dict, db: AsyncSession) -> Course:
    """
    Create a new course using the provided data.
    """
    new_course = Course(
        title=course_data["title"],
        description=course_data["description"],
        image_url=course_data["image_url"],
        level=course_data["level"],
        duration=course_data["duration"],
        price=course_data["price"]
    )
    db.add(new_course)
    await db.commit()
    await db.refresh(new_course)
    return new_course

async def delete_course(course_id: str, db: AsyncSession) -> Course:
    """
    Delete a course by its ID.
    """
    course = await get_course_by_id(course_id, db)
    if not course:
        raise ValueError("Course not found")
    try:
        await db.delete(course)
    except NoResultFound:
        raise ValueError("Course not found")
    except IntegrityError:
        raise ValueError("Course is associated with other records and cannot be deleted.")
    await db.commit()
    await db.refresh(new_course)
    return new_course

async def update_course(course_id: str, course_data: dict, db: AsyncSession) -> Optional[Course]:
    """
    Update an existing course with the provided data.
    """
    course = await get_course_by_id(course_id, db)
    if not course:
        return None
    for key, value in course_data.items():
        if value is not None:
            setattr(course, key, value)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


# Retrieve course content: modules and their lessons
async def get_course_content(course_id: str, db: AsyncSession) -> Optional[Course]:
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(
            selectinload(Course.modules).selectinload(Module.lessons)
        )
    )
    course = result.scalars().first()
    return course

# Enroll the current user in a course
async def enroll_in_course(course_id: str, current_user: User, db: AsyncSession) -> bool:
    # Check if the user is already enrolled
    result = await db.execute(
        select(UserCourse).where(
            (UserCourse.user_id == current_user.id) &
            (UserCourse.course_id == course_id)
        )
    )
    enrollment = result.scalars().first()
    if enrollment:
        # Already enrolled; no need to add again.
        return False

    # Create a new enrollment record
    new_enrollment = UserCourse(
        user_id=current_user.id,
        course_id=course_id,
        progress=0.0  # Starting progress
    )
    db.add(new_enrollment)
    await db.commit()
    return True

async def check_and_mark_course_completion(user_id: str, course_id: str, db: AsyncSession) -> None:
    """
    Check if the user's enrollment in the specified course has reached 100% progress.
    If so, mark the course as completed and send a notification.
    """
    result = await db.execute(
        select(UserCourse).where(
            UserCourse.user_id == user_id,
            UserCourse.course_id == course_id
        )
    )
    enrollment = result.scalars().first()
    if enrollment and enrollment.progress >= 100 and enrollment.completed_at is None:
        enrollment.completed_at = datetime.now(timezone.utc)
        db.add(enrollment)
        await db.commit()
        # Send notification that the course is completed.
        await create_notification(
            user_id,
            "Course Completed",
            f"You have completed the course successfully!",
            db
        )
