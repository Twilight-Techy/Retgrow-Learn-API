# src/courses/schemas.py

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from src.models.models import CourseLevel

class CourseResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: CourseLevel
    duration: Optional[str] = None
    price: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CourseCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: CourseLevel
    duration: Optional[str] = None
    price: float

class CourseUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: Optional[CourseLevel] = None
    duration: Optional[str] = None
    price: Optional[float] = None

class LessonCreateSchema(BaseModel):
    title: str
    content: Optional[str] = None
    video_url: Optional[str] = None
    order: int

class ModuleCreateSchema(BaseModel):
    title: str
    order: int
    lessons: List[LessonCreateSchema] = []

class CourseCreateWithContentRequest(CourseCreateRequest):
    """
    Schema for creating a course with its modules and lessons.
    Inherits from CourseCreateRequest and adds a list of modules.
    """
    modules: List[ModuleCreateSchema] = []

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
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: CourseLevel
    duration: Optional[str] = None
    price: float
    modules: List[ModuleResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EnrollmentResponse(BaseModel):
    message: str