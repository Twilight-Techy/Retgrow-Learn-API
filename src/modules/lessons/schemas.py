# src/lessons/schemas.py

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID
from pydantic import ConfigDict, BaseModel

class LessonResponse(BaseModel):
    id: UUID
    module_title: str
    title: str
    content: Optional[List[Any]] = None
    video_url: Optional[str] = None
    order: int
    completed: bool = False
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CompleteLessonResponse(BaseModel):
    message: str

class LessonCreateRequest(BaseModel):
    title: str
    content: Optional[str] = None
    video_url: Optional[str] = None
    order: int
    model_config = ConfigDict(from_attributes=True)

class LessonUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    video_url: Optional[str] = None
    order: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class LastLessonResponse(BaseModel):
    lesson_id: Optional[UUID] = None
    model_config = ConfigDict(from_attributes=True)