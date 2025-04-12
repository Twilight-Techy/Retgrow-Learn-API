# src/instructor/schemas.py

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class CourseResponse(BaseModel):
    id: UUID
    track_id: UUID
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: str
    duration: Optional[str] = None
    price: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CourseCreateRequest(BaseModel):
    track_id: UUID
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: str
    duration: Optional[str] = None
    price: float

class CourseUpdateRequest(BaseModel):
    track_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: Optional[str] = None
    duration: Optional[str] = None
    price: Optional[float] = None

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