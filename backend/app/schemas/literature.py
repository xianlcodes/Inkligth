from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class LiteratureBase(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    year: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    status: Optional[str] = "unread"


class LiteratureCreate(LiteratureBase):
    file_path: str
    raw_text: Optional[str] = None


class LiteratureUpdate(BaseModel):
    status: Optional[str] = None


class LiteratureResponse(LiteratureBase):
    id: str
    user_id: str
    file_path: str
    raw_text: Optional[str] = None
    translated_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LiteratureListResponse(BaseModel):
    total: int
    items: list[LiteratureResponse]
