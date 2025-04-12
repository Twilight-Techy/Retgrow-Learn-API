# src/resources/schemas.py

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class ResourceResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    type: str
    url: str
    track_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ResourceViewResponse(BaseModel):
    message: str

    class Config:
        from_attributes = True

class ResourceCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    type: str
    url: str
    track_id: Optional[str] = None

    class Config:
        from_attributes = True

class ResourceUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    track_id: Optional[str] = None

    class Config:
        from_attributes = True