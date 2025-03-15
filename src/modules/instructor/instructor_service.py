# src/instructor/course_service.py

from typing import List, Optional
import uuid
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.models import Course, Deadline

async def list_courses(db: AsyncSession) -> List[Course]:
    """
    Retrieve all courses available for management.
    """
    stmt = select(Course).order_by(Course.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

async def get_course_by_id(course_id: str, db: AsyncSession) -> Optional[Course]:
    """
    Retrieve a specific course by its ID.
    """
    stmt = select(Course).where(Course.id == course_id)
    result = await db.execute(stmt)
    return result.scalars().first()

async def create_course(course_data: dict, db: AsyncSession) -> Course:
    """
    Create a new course using the provided data.
    """
    new_course = Course(
        track_id=course_data["track_id"],
        title=course_data["title"],
        description=course_data.get("description"),
        image_url=course_data.get("image_url"),
        level=course_data["level"],
        duration=course_data.get("duration"),
        price=course_data["price"]
    )
    db.add(new_course)
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

async def create_deadline(deadline_data: dict, db: AsyncSession) -> Deadline:
    """
    Create a new deadline record using the provided data.
    """
    new_deadline = Deadline(
        # If your model auto-generates the UUID, you can omit this.
        id=uuid.uuid4(),
        title=deadline_data["title"],
        description=deadline_data.get("description"),
        due_date=deadline_data["due_date"],
        course_id=deadline_data.get("course_id")
    )
    db.add(new_deadline)
    await db.commit()
    await db.refresh(new_deadline)
    return new_deadline