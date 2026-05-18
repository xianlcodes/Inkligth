from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TutorialCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(default="")
    summary: Optional[str] = Field(None, max_length=500)


class TutorialUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    summary: Optional[str] = Field(None, max_length=500)
    is_published: Optional[bool] = None


class TutorialResponse(BaseModel):
    id: str
    title: str
    content: str
    summary: Optional[str] = None
    is_published: bool
    published_at: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    version_count: int = 0

    class Config:
        from_attributes = True


class TutorialListResponse(BaseModel):
    total: int
    items: list[TutorialResponse]


class TutorialVersionResponse(BaseModel):
    id: str
    tutorial_id: str
    version_number: int
    title: str
    content: str
    summary: Optional[str] = None
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class TutorialVersionListResponse(BaseModel):
    items: list[TutorialVersionResponse]