from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class FolderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)


class FolderResponse(BaseModel):
    id: str
    user_id: str
    name: str
    parent_id: Optional[str] = None
    literature_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FolderListResponse(BaseModel):
    items: list[FolderResponse]
