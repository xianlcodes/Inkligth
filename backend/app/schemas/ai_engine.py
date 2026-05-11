from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional


class AIEngineBase(BaseModel):
    provider: str = Field(..., min_length=1, max_length=50)
    api_base: str = Field(..., min_length=1)
    default_model: str = Field(..., min_length=1)
    fallback_models: Optional[str] = None
    is_default: bool = False


class AIEngineCreate(AIEngineBase):
    api_key: str = Field(..., min_length=1)


class AIEngineUpdate(BaseModel):
    provider: Optional[str] = Field(None, min_length=1, max_length=50)
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    fallback_models: Optional[str] = None
    is_default: Optional[bool] = None


class AIEngineResponse(BaseModel):
    id: str
    user_id: str
    provider: str
    api_base: str
    api_key_mask: str
    default_model: str
    fallback_models: Optional[str] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIEngineListResponse(BaseModel):
    total: int
    items: list[AIEngineResponse]


class AIEngineTestResult(BaseModel):
    success: bool
    message: str
    models: list[str] = []
