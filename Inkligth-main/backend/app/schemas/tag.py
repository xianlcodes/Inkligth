from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class TagResponse(BaseModel):
    id: str
    user_id: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class TagCloudItem(BaseModel):
    name: str
    count: int


class TagCloudResponse(BaseModel):
    tags: list[TagCloudItem]


class LiteratureTagsResponse(BaseModel):
    literature_id: str
    tags: list[TagResponse]