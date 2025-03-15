# src/leaderboard/schemas.py

from pydantic import BaseModel

class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    xp: int
    avatar: str

    class Config:
        from_attributes = True
