from pydantic import BaseModel
from datetime import datetime


class RefreshTokenCreate(BaseModel):
    user_id: str


class RefreshTokenResponse(BaseModel):
    id: str
    user_id: str
    token: str
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenWithRefresh(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_admin: bool = False
