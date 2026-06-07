from pydantic import BaseModel
from datetime import datetime, date


class StorageResponse(BaseModel):
    total_space: int
    used_space: int
    remaining_space: int
    base_space: int
    check_in_bonus: int
    invitation_bonus: int

    class Config:
        from_attributes = True


class CheckInStatusResponse(BaseModel):
    checked_in_today: bool
    streak_days: int
    today_reward: int
    checked_dates: list[date]
    next_milestone_reward: int = 0
    next_milestone_day: int | None = None


class CheckInResponse(BaseModel):
    streak_days: int
    reward_bytes: int
    total_check_in_bonus: int


class InvitedUser(BaseModel):
    email: str
    registered_at: datetime
    reward_granted: bool


class InvitationCodeResponse(BaseModel):
    code: str
    is_active: bool
    created_at: datetime


class InvitationListResponse(BaseModel):
    codes: list[InvitationCodeResponse]
    invited_users: list[InvitedUser]
    invite_url: str


class GenerateCodeResponse(BaseModel):
    code: str