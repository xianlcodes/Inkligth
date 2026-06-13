from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional

from app.utils.compression import decompress_json


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
    file_size: Optional[int] = None
    raw_text: Optional[str] = None
    folder_id: Optional[str] = None


class LiteratureUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    year: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    status: Optional[str] = None
    folder_id: Optional[str] = None
    raw_text: Optional[str] = None
    last_read_page: Optional[int] = None
    total_pages: Optional[int] = None


class LiteratureResponse(LiteratureBase):
    id: str
    user_id: str
    file_path: str
    file_size: Optional[int] = None
    raw_text: Optional[str] = None
    translated_text: Optional[str] = None
    translated_at: Optional[datetime] = None
    folder_id: Optional[str] = None
    total_pages: Optional[int] = None
    last_read_page: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @field_validator('translated_text', mode='before')
    @classmethod
    def decompress_translated_text(cls, v):
        if isinstance(v, bytes):
            return decompress_json(v)
        return v

    class Config:
        from_attributes = True


class LiteratureListResponse(BaseModel):
    total: int
    items: list[LiteratureResponse]
