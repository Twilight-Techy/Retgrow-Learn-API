# src/deadlines/schemas.py

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class DeadlineCreateRequest(BaseModel):
    title: str
    description: str | None = None
    due_date: datetime
    # Optionally, a deadline may be tied to a course; adjust as needed.
    course_id: UUID | None = None

    class Config:
        from_attributes = True

class DeadlineResponse(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    due_date: datetime
    course_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True