# src/resources/schemas.py

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, model_validator

class ResourceResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    type: Optional[str] = None
    url: str
    track_id: Optional[UUID] = None
    track_title: Optional[str] = None
    track_slug: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def from_orm(cls, data):
        if isinstance(data, dict):
            return data
        track = getattr(data, 'track', None)
        return {
            'id': data.id,
            'title': data.title,
            'description': data.description,
            'image_url': getattr(data, 'image_url', None),
            'type': data.type.value if hasattr(data.type, 'value') else str(data.type) if data.type else None,
            'url': data.url,
            'track_id': data.track_id,
            'track_title': track.title if track else None,
            'track_slug': getattr(track, 'slug', None) if track else None,
            'created_at': data.created_at,
            'updated_at': data.updated_at,
        }

class ResourceViewResponse(BaseModel):
    message: str

    class Config:
        from_attributes = True

class ResourceCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    type: str
    url: str
    track_id: Optional[UUID] = None

    class Config:
        from_attributes = True

class ResourceUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    track_id: Optional[UUID] = None

    class Config:
        from_attributes = True