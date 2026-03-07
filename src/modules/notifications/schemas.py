# src/notifications/schemas.py

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import ConfigDict, BaseModel

class NotificationResponse(BaseModel):
    id: UUID
    type: str
    title: str
    message: str
    created_at: datetime
    course_id: Optional[UUID] = None
    track_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    action_url: Optional[str] = None
    # computed flag for frontend
    is_unread: bool
    model_config = ConfigDict(from_attributes=True)

class NotificationUpdateResponse(BaseModel):
    message: str

class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    has_more: bool
