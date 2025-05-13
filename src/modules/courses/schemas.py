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

    class Config:
        from_attributes = True

class CourseUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: Optional[CourseLevel] = None
    duration: Optional[str] = None
    price: Optional[float] = None

    class Config:
        from_attributes = True

class LessonCreateSchema(BaseModel):
    title: str
    content: Optional[str] = None
    video_url: Optional[str] = None
    order: int

    class Config:
        from_attributes = True

class LessonUpdateSchema(BaseModel):
    id: UUID  # Required to identify which lesson to update
    title: Optional[str] = None
    content: Optional[str] = None
    video_url: Optional[str] = None
    order: Optional[int] = None

    class Config:
        from_attributes = True

class ModuleCreateSchema(BaseModel):
    title: str
    order: int
    lessons: List[LessonCreateSchema] = []

    class Config:
        from_attributes = True

class ModuleUpdateSchema(BaseModel):
    id: UUID  # Required to identify which module to update
    title: Optional[str] = None
    order: Optional[int] = None
    lessons: Optional[List[LessonUpdateSchema]] = None

    class Config:
        from_attributes = True

class CourseCreateWithContentRequest(CourseCreateRequest):
    """
    Schema for creating a course with its modules and lessons.
    Inherits from CourseCreateRequest and adds a list of modules.
    """
    modules: List[ModuleCreateSchema] = []

class CourseUpdateWithContentRequest(CourseUpdateRequest):
    """
    Schema for updating a course with its modules and lessons.
    Inherits from CourseUpdateRequest and adds a list of modules.
    Modules can be added, updated, or removed based on presence/absence in the list.
    """
    modules: Optional[List[ModuleUpdateSchema]] = None

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