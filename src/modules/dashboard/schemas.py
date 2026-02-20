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
    description: Optional[str] = None
    type: str
    url: str
    track_title: Optional[str] = None

    class Config:
        from_attributes = True

class DeadlineResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    due_date: datetime
    course: Optional[str] = None
    is_overdue: bool

    class Config:
        from_attributes = True

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

class CourseBrief(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

class TrackBrief(BaseModel):
    id: UUID
    slug: Optional[str] = None
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

class LearningPathResponse(BaseModel):
    id: UUID
    user_id: UUID
    track: TrackBrief
    current_course_id: Optional[UUID] = None
    progress: float
    courses: List[CourseBrief] = []  # first N courses for preview (ordered)
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CertificateBrief(BaseModel):
    id: str
    course_id: str
    course_title: str
    certificate_url: Optional[str] = None
    issued_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AggregatedDashboardResponse(BaseModel):
    """Single response combining all dashboard data."""
    enrolled_courses: List[EnrolledCourseResponse] = []
    recent_resources: List[RecentResourceResponse] = []
    upcoming_deadlines: List[DeadlineResponse] = []
    recent_achievements: List[RecentAchievementResponse] = []
    progress_overview: List[ProgressOverviewItem] = []
    recommended_courses: List[CourseResponse] = []
    learning_path: Optional[LearningPathResponse] = None
    certificates: List[CertificateBrief] = []

    class Config:
        from_attributes = True