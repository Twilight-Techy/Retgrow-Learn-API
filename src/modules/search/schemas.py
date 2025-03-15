# src/search/schemas.py

from typing import List, Optional
from pydantic import BaseModel

class SearchResultItem(BaseModel):
    id: str
    type: str  # e.g. "course", "track", "resource"
    title: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class SearchResponse(BaseModel):
    courses: List[SearchResultItem]
    tracks: List[SearchResultItem]
    resources: List[SearchResultItem]
