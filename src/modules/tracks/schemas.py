# src/tracks/schemas.py

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import ConfigDict, BaseModel

class TrackResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: Optional[str] = None
    duration: Optional[str] = None
    prerequisites: Optional[List[str]] = []

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class TrackCreateRequest(BaseModel):
    slug: str
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: str
    duration: Optional[str] = None
    prerequisites: Optional[List[str]] = None  # List of prerequisites
    model_config = ConfigDict(from_attributes=True)

class TrackUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: Optional[str] = None
    duration: Optional[str] = None
    prerequisites: Optional[List[str]] = None
    model_config = ConfigDict(from_attributes=True)

class TrackCourseUpdate(BaseModel):
    course_id: UUID
    order: int

class UpdateTrackCoursesRequest(BaseModel):
    courses: List[TrackCourseUpdate]
    model_config = ConfigDict(from_attributes=True)

class LessonResponse(BaseModel):
    id: UUID
    title: str
    order: int
    model_config = ConfigDict(from_attributes=True)

class ModuleResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    order: int
    lessons: List[LessonResponse] = []
    model_config = ConfigDict(from_attributes=True)

class CurriculumCourseResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    order: int  # Order of the course in this track
    modules: List[ModuleResponse] = []
    model_config = ConfigDict(from_attributes=True)