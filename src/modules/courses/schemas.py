# src/courses/schemas.py

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class CourseResponse(BaseModel):
    id: str
    track_id: str
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

# For the course content endpoint we assume a course is composed of modules that contain lessons.
class LessonResponse(BaseModel):
    id: str
    title: str
    content: Optional[str] = None
    video_url: Optional[str] = None
    order: int

    class Config:
        from_attributes = True

class ModuleResponse(BaseModel):
    id: str
    title: str
    order: int
    lessons: List[LessonResponse] = []

    class Config:
        from_attributes = True

class CourseDetailResponse(BaseModel):
    id: str
    track_id: str
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: str
    duration: Optional[str] = None
    price: float
    modules: List[ModuleResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EnrollmentResponse(BaseModel):
    message: str
