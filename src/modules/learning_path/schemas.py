# src/learning_path/schemas.py

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import ConfigDict, BaseModel

class SkillResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class UserSkillResponse(BaseModel):
    skill: SkillResponse
    proficiency: float          # 0..100
    last_updated: datetime
    model_config = ConfigDict(from_attributes=True)

class LearningPathEnrollRequest(BaseModel):
    track_id: str  # The track the user wants to enroll in
    model_config = ConfigDict(from_attributes=True)

class LearningPathResponse(BaseModel):
    id: UUID
    user_id: UUID
    track_id: UUID
    progress: float
    current_course_id: Optional[UUID] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)