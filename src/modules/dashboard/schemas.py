# src/dashboard/schemas.py

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, model_validator

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
    type: Optional[str] = None
    url: str
    track_title: Optional[str] = None

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def from_orm(cls, data):
        if isinstance(data, dict):
            return data
        return {
            'id': data.id,
            'title': data.title,
            'description': data.description,
            'type': data.type.value if hasattr(data.type, 'value') else str(data.type) if data.type else None,
            'url': data.url,
            'track_title': data.track.title if getattr(data, 'track', None) else None,
        }

class DeadlineResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    due_date: datetime
    course: Optional[str] = None
    is_overdue: bool = False

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def from_orm(cls, data):
        if isinstance(data, dict):
            return data
        is_overdue = False
        try:
            is_overdue = data.due_date is not None and data.due_date < datetime.now(timezone.utc)
        except Exception:
            pass
        return {
            'id': data.id,
            'title': data.title,
            'description': data.description,
            'due_date': data.due_date,
            'course': data.course.title if getattr(data, 'course', None) else None,
            'is_overdue': is_overdue,
        }

class RecentAchievementResponse(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    icon_url: str | None = None
    earned_at: datetime

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def from_orm(cls, data):
        if isinstance(data, dict):
            return data
        # Flatten UserAchievement -> Achievement fields
        achievement = getattr(data, 'achievement', None)
        if achievement:
            return {
                'id': achievement.id,
                'title': achievement.title,
                'description': achievement.description,
                'icon_url': getattr(achievement, 'icon_url', None),
                'earned_at': data.earned_at,
            }
        return data

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

    @model_validator(mode='before')
    @classmethod
    def from_orm(cls, data):
        if isinstance(data, dict):
            return data
        return {
            'id': str(data.id),
            'course_id': str(data.course_id),
            'course_title': data.course.title if getattr(data, 'course', None) else 'Unknown Course',
            'certificate_url': getattr(data, 'certificate_url', None),
            'issued_at': getattr(data, 'issued_at', None),
        }


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