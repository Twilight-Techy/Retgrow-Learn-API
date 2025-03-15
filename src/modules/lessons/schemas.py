# src/lessons/schemas.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class LessonResponse(BaseModel):
    id: str
    module_id: str
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
