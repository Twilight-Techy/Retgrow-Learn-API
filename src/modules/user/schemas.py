# src/user/schemas.py

from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from datetime import datetime

class ProfileResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    bio: str | None = None
    avatar_url: str | None = None
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

class CourseProgress(BaseModel):
    course_id: UUID
    progress: float

    class Config:
        from_attributes = True

class UserProgressResponse(BaseModel):
    overall_progress: float
    courses: List[CourseProgress]