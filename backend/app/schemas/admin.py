from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class StatsOverview(BaseModel):
    total_users: int
    total_literatures: int
    total_read_literatures: int
    total_unread_literatures: int
    total_reading_literatures: int
    total_notes: int
    total_presentations: int


class TrendPoint(BaseModel):
    date: str
    value: int


class TimeSeriesStats(BaseModel):
    new_users: list[TrendPoint]
    new_literatures: list[TrendPoint]
    reading_activity: list[TrendPoint]


class UserListItem(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    is_admin: bool
    literature_count: int
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    total: int
    items: list[UserListItem]


class UserUpdateAdmin(BaseModel):
    is_admin: Optional[bool] = None
    password: Optional[str] = None


class OperationLogItem(BaseModel):
    id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    resource: Optional[str] = None
    resource_id: Optional[str] = None
    detail: Optional[str] = None
    ip_address: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class OperationLogListResponse(BaseModel):
    total: int
    items: list[OperationLogItem]


class SystemConfigItem(BaseModel):
    id: str
    key: str
    value: Optional[str] = None
    category: str = "general"
    config_type: str = "text"
    label: Optional[str] = None
    description: Optional[str] = None
    default_value: Optional[str] = None
    valid_values: Optional[str] = None
    example: Optional[str] = None
    is_critical: bool = False
    requires_restart: bool = False
    scope: str = "admin"
    sort_order: int = 0
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemConfigListResponse(BaseModel):
    items: list[SystemConfigItem]


class SystemConfigCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=200)
    value: Optional[str] = None
    category: str = "general"
    config_type: str = "text"
    label: Optional[str] = None
    description: Optional[str] = None
    default_value: Optional[str] = None
    valid_values: Optional[str] = None
    example: Optional[str] = None
    is_critical: bool = False
    requires_restart: bool = False
    scope: str = "admin"
    sort_order: int = 0


class SystemConfigUpdate(BaseModel):
    value: Optional[str] = None
    category: Optional[str] = None
    config_type: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    default_value: Optional[str] = None
    valid_values: Optional[str] = None
    example: Optional[str] = None
    is_critical: Optional[bool] = None
    requires_restart: Optional[bool] = None
    scope: Optional[str] = None
    sort_order: Optional[int] = None


class ConfigChangeLogItem(BaseModel):
    id: str
    config_key: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: Optional[str] = None
    changed_at: datetime

    class Config:
        from_attributes = True


class ConfigChangeLogListResponse(BaseModel):
    items: list[ConfigChangeLogItem]
