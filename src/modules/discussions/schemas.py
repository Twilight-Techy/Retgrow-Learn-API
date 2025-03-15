# src/discussions/schemas.py

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class DiscussionReplyResponse(BaseModel):
    id: str
    discussion_id: str
    user_id: str
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DiscussionResponse(BaseModel):
    id: str
    course_id: str
    user_id: str
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
