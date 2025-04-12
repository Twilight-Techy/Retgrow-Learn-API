# src/notifications/schemas.py

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class NotificationResponse(BaseModel):
    id: UUID
    type: str
    message: str
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationUpdateResponse(BaseModel):
    message: str
