from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    username: str | None = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: str
    is_admin: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool = False


class TokenPayload(BaseModel):
    sub: str | None = None
