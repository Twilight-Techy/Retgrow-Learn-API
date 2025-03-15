# src/learning_path/schemas.py

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel

class LearningPathResponse(BaseModel):
    id: str
    user_id: str
    track_id: str
    current_course_id: str
    progress: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SkillResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class UserSkillResponse(BaseModel):
    skill: SkillResponse
    proficiency: float
    last_updated: datetime

    class Config:
        from_attributes = True

class LearningPathEnrollRequest(BaseModel):
    track_id: str  # The track the user wants to enroll in

    class Config:
        from_attributes = True

class LearningPathResponse(BaseModel):
    id: UUID
    user_id: UUID
    track_id: UUID
    progress: float
    current_course_id: Optional[UUID] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True