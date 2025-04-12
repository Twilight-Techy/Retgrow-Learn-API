# src/lessons/schemas.py

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class LessonResponse(BaseModel):
    id: UUID
    module_id: UUID
    title: str
    content: Optional[str] = None
    video_url: Optional[str] = None
    order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CompleteLessonResponse(BaseModel):
    message: str
