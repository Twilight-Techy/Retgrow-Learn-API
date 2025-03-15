# src/notifications/schemas.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class NotificationResponse(BaseModel):
    id: str
    type: str
    message: str
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationUpdateResponse(BaseModel):
    message: str
