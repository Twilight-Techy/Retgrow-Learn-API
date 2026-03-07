# src/achievements/schemas.py

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import ConfigDict, BaseModel

class AchievementResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserAchievementResponse(BaseModel):
    achievement: AchievementResponse
    earned_at: datetime
    model_config = ConfigDict(from_attributes=True)

class LevelResponse(BaseModel):
    level: int
    xp: int
    nextLevelXp: int
    model_config = ConfigDict(from_attributes=True)
