# src/tracks/schemas.py

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

class TrackResponse(BaseModel):
    # id: UUID
    # slug: str
    title: str
    description: str | None = None
    image_url: str | None = None
    # level: str
    # duration: str | None = None
    # prerequisites: List[str] = []
    # created_at: datetime
    # updated_at: datetime

    class Config:
        from_attributes = True

class TrackCreateRequest(BaseModel):
    slug: str
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: str
    duration: Optional[str] = None
    prerequisites: Optional[List[str]] = None  # List of prerequisites

    class Config:
        from_attributes = True

class TrackUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    level: Optional[str] = None
    duration: Optional[str] = None
    prerequisites: Optional[List[str]] = None

    class Config:
        from_attributes = True

class ModuleResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    order: int

    class Config:
        from_attributes = True

class CurriculumCourseResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    order: int  # Order of the course in this track
    modules: List[ModuleResponse] = []

    class Config:
        from_attributes = True

class TrackCurriculumResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    prerequisites: List[str] = []  # List of topics the user must know to take this track
    order: int
    modules: List[ModuleResponse]

    class Config:
        from_attributes = True

class TrackCourseUpdate(BaseModel):
    course_id: UUID
    order: int

class UpdateTrackCoursesRequest(BaseModel):
    courses: List[TrackCourseUpdate]

    class Config:
        from_attributes = True