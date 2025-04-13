# src/instructor/course_service.py

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.models import Deadline



async def create_deadline(deadline_data: dict, db: AsyncSession) -> Deadline:
    """
    Create a new deadline record using the provided data.
    """
    new_deadline = Deadline(
        # If your model auto-generates the UUID, you can omit this.
        id=uuid.uuid4(),
        title=deadline_data["title"],
        description=deadline_data["description"],
        due_date=deadline_data["due_date"],
        course_id=deadline_data["course_id"] if "course_id" in deadline_data else None,
    )
    db.add(new_deadline)
    await db.commit()
    await db.refresh(new_deadline)
    return new_deadline