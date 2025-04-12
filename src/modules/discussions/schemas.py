# src/discussions/schemas.py

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

class DiscussionReplyResponse(BaseModel):
    id: UUID
    discussion_id: UUID
    user_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DiscussionResponse(BaseModel):
    id: UUID
    course_id: UUID
    user_id: UUID
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    # Optionally include replies if needed (you can omit or include them based on your use case)
    replies: List[DiscussionReplyResponse] = []

    class Config:
        from_attributes = True

class DiscussionCreateRequest(BaseModel):
    title: str
    content: str

class DiscussionReplyCreateRequest(BaseModel):
    content: str
