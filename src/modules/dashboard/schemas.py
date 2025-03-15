# src/dashboard/schemas.py

from datetime import datetime
from typing import List
from pydantic import BaseModel

# Reuse CourseResponse from courses if available;
# otherwise, define a minimal enrolled course schema.
class EnrolledCourseResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    image_url: str | None = None
    level: str
    duration: str | None = None
    price: float

    class Config:
        from_attributes = True

# Reuse ResourceResponse from resources if available;
# otherwise, define a minimal resource schema.
class RecentResourceResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    type: str
    url: str

    class Config:
        from_attributes = True

# A simple deadline schema; in a real app this would come from a dedicated Deadline model.
class DeadlineResponse(BaseModel):
    id: str
    title: str
    due_date: datetime

    class Config:
        from_attributes = True

# Dashboard aggregated response.
class DashboardResponse(BaseModel):
    enrolled_courses: List[EnrolledCourseResponse]
    recent_resources: List[RecentResourceResponse]
    upcoming_deadlines: List[DeadlineResponse]

class RecentAchievementResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    icon_url: str | None = None
    earned_at: datetime

    class Config:
        from_attributes = True

class ProgressOverviewItem(BaseModel):
    name: str
    value: int

    class Config:
        from_attributes = True
