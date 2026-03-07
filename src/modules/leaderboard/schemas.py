# src/leaderboard/schemas.py

from typing import Optional
from uuid import UUID
from pydantic import ConfigDict, BaseModel

class LeaderboardEntry(BaseModel):
    id: UUID
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    xp: int
    model_config = ConfigDict(from_attributes=True)
