from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    username: str | None = None


class UserCreate(UserBase):
    password: str
    captcha_id: str
    captcha_answer: str
    email_verification_code: str
    agreed_to_terms: bool = False
    invite_code: str | None = None



class UserResponse(UserBase):
    id: str
    is_admin: bool = False
    avatar_style: str | None = None
    theme_color: str | None = None
    tutorial_completed: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: str | None = None
    avatar_style: str | None = None
    theme_color: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool = False


class TokenPayload(BaseModel):
    sub: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str


class VerifyResetCodeResponse(BaseModel):
    verification_id: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    verification_id: str
    new_password: str


class SendVerificationCodeRequest(BaseModel):
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    code: str
    new_password: str
