# src/lessons/schemas.py

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel

class LessonResponse(BaseModel):
    id: UUID
    module_id: UUID
    title: str
    content: Optional[List[Any]] = None
    video_url: Optional[str] = None
    order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CompleteLessonResponse(BaseModel):
    message: str

class LessonCreateRequest(BaseModel):
    title: str
    content: Optional[str] = None
    video_url: Optional[str] = None
    order: int

    class Config:
        from_attributes = True

class LessonUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    video_url: Optional[str] = None
    order: Optional[int] = None

    class Config:
        from_attributes = True

class LastLessonResponse(BaseModel):
    lesson_id: Optional[UUID]

    class Config:
        from_attributes = True