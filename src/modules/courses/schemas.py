# src/courses/schemas.py

from datetime import datetime
from typing import List, Optional
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
    track_id: Optional[UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: Optional[str] = None
    duration: Optional[str] = None
    price: Optional[float] = None

# For the course content endpoint we assume a course is composed of modules that contain lessons.
class LessonResponse(BaseModel):
    id: UUID
    title: str
    content: Optional[str] = None
    video_url: Optional[str] = None
    order: int

    class Config:
        from_attributes = True

class ModuleResponse(BaseModel):
    id: UUID
    title: str
    order: int
    lessons: List[LessonResponse] = []

    class Config:
        from_attributes = True

class CourseDetailResponse(BaseModel):
    id: UUID
    track_id: UUID
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
