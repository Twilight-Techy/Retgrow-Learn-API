# src/dashboard/schemas.py

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from src.models.models import CourseLevel

# Reuse CourseResponse from courses if available;
# otherwise, define a minimal enrolled course schema.
class EnrolledCourseResponse(BaseModel):
    id: UUID
    title: str
    progress: float = 0.00

    class Config:
        from_attributes = True

class RecentResourceResponse(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    type: str
    url: str

    class Config:
        from_attributes = True

class DeadlineResponse(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    due_date: datetime

    class Config:
        from_attributes = True

# Dashboard aggregated response.
class DashboardResponse(BaseModel):
    enrolled_courses: List[EnrolledCourseResponse]
    recent_resources: List[RecentResourceResponse]
    upcoming_deadlines: List[DeadlineResponse]

class RecentAchievementResponse(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    earned_at: datetime

    class Config:
        from_attributes = True

class ProgressOverviewItem(BaseModel):
    name: str
    value: int

    class Config:
        from_attributes = True

class CourseResponse(BaseModel):
    id: UUID
    track_id: UUID
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