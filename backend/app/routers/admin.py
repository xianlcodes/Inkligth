import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.admin import (
    StatsOverview,
    TimeSeriesStats,
    UserListItem,
    UserListResponse,
    UserUpdateAdmin,
    OperationLogItem,
    OperationLogListResponse,
    SystemConfigItem,
    SystemConfigListResponse,
    SystemConfigCreate,
    SystemConfigUpdate,
    ConfigChangeLogItem,
    ConfigChangeLogListResponse,
)
from app.services.admin_service import AdminService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


def _check_admin(current_user: User):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可执行此操作")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
@router.get("/stats/overview", response_model=StatsOverview)
async def get_stats_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    data = await AdminService.get_overview(db)
    return StatsOverview(**data)


@router.get("/stats/timeseries", response_model=TimeSeriesStats)
async def get_stats_timeseries(
    period: str = Query("day", pattern="^(day|week|month|year)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    data = await AdminService.get_timeseries_stats(db, period)
    return TimeSeriesStats(**data)


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------
@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str = Query(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    total, items = await AdminService.list_users(db, skip=skip, limit=limit, search=search)
    return UserListResponse(
        total=total,
        items=[UserListItem(**item) for item in items],
    )


@router.patch("/users/{user_id}")
async def update_user_admin(
    user_id: str,
    data: UserUpdateAdmin,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    target = await UserService.get_user_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if target.id == current_user.id and data.is_admin is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能取消自己的管理员权限")

    updated = await AdminService.update_user(db, target, data.model_dump(exclude_unset=True))

    await AdminService.create_log(
        db,
        user_id=str(current_user.id),
        user_email=current_user.email,
        action="update_user",
        resource="user",
        resource_id=user_id,
        detail=f"Updated user {target.email}: {data.model_dump(exclude_unset=True)}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "用户已更新"}


# ---------------------------------------------------------------------------
# Operation logs
# ---------------------------------------------------------------------------
@router.get("/logs", response_model=OperationLogListResponse)
async def list_operation_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    total, items = await AdminService.list_logs(db, skip=skip, limit=limit, user_id=user_id, action=action)
    return OperationLogListResponse(
        total=total,
        items=[OperationLogItem.model_validate(log) for log in items],
    )


# ---------------------------------------------------------------------------
# System config
# ---------------------------------------------------------------------------
@router.get("/config", response_model=SystemConfigListResponse)
async def list_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    items = await AdminService.get_all_configs(db)
    return SystemConfigListResponse(
        items=[SystemConfigItem.model_validate(cfg) for cfg in items],
    )


@router.post("/config", response_model=SystemConfigItem, status_code=status.HTTP_201_CREATED)
async def create_config(
    data: SystemConfigCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    cfg = await AdminService.upsert_config(
        db, key=data.key, data=data.model_dump(exclude={"key"}), updated_by=current_user.email,
    )
    await AdminService.create_change_log(db, data.key, None, cfg.value, current_user.email)
    await AdminService.create_log(
        db, user_id=str(current_user.id), user_email=current_user.email,
        action="create_config", resource="system_config", resource_id=data.key,
        detail=f"Created config {data.key}", ip_address=request.client.host if request.client else None,
    )
    return SystemConfigItem.model_validate(cfg)


@router.put("/config/{key}")
async def update_config(
    key: str,
    data: SystemConfigUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    existing = await AdminService.get_config(db, key)
    old_val = existing.value if existing else None

    cfg = await AdminService.upsert_config(
        db, key=key, data=data.model_dump(exclude_unset=True), updated_by=current_user.email,
    )
    if old_val != cfg.value:
        await AdminService.create_change_log(db, key, old_val, cfg.value, current_user.email)
    await AdminService.create_log(
        db, user_id=str(current_user.id), user_email=current_user.email,
        action="update_config", resource="system_config", resource_id=key,
        detail=f"Updated config {key}: {cfg.value[:200] if cfg.value else ''}",
        ip_address=request.client.host if request.client else None,
    )
    return SystemConfigItem.model_validate(cfg)


@router.delete("/config/{key}")
async def delete_config(
    key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    deleted = await AdminService.delete_config(db, key)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置项不存在")
    await AdminService.create_log(
        db, user_id=str(current_user.id), user_email=current_user.email,
        action="delete_config", resource="system_config", resource_id=key,
        detail=f"Deleted config {key}", ip_address=request.client.host if request.client else None,
    )
    return {"message": "配置已删除"}


@router.get("/config/{key}/history", response_model=ConfigChangeLogListResponse)
async def get_config_history(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    logs = await AdminService.get_change_logs(db, config_key=key)
    return ConfigChangeLogListResponse(
        items=[ConfigChangeLogItem.model_validate(log) for log in logs],
    )
