# src/achievements/schemas.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class AchievementResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserAchievementResponse(BaseModel):
    achievement: AchievementResponse
    earned_at: datetime

    class Config:
        from_attributes = True

class LevelResponse(BaseModel):
    level: int
    xp: int
    nextLevelXp: int

    class Config:
        from_attributes = True
