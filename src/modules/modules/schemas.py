from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

class ModuleCreateRequest(BaseModel):
    title: str = Field(..., description="Title of the new module")
    order: int = Field(..., ge=1, description="Position of the module within the course")

class ModuleUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, description="Updated title of the module")
    order: Optional[int] = Field(None, ge=1, description="Updated position of the module within the course")

class ModuleResponse(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True