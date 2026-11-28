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
    # 平台免费额度信息（/users/me 实时返回；其余路径用默认值）
    has_ai_engine: bool = False           # 是否已配置自己的 AI 引擎
    free_translations: int = 0            # 平台免费额度今日剩余（次，含赠送余额）
    free_translations_used: int = 0       # 累计消耗次数
    prefer_free_quota: bool = False       # 翻译通道偏好：优先使用免费额度
    free_quota_unlimited: bool = False    # 平台不限量模式（-1）：免费额度永不耗尽
    free_quota_daily_limit: int = 0       # 每日免费次数上限（正数 = 每日限额模式）

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
