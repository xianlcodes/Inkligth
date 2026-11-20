import logging
from typing import Optional
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_user_db as get_db, get_tencent_db
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
    SystemLogFileItem,
    SystemLogFileStats,
    SystemLogFileListResponse,
    SystemLogContentResponse,
    SystemLogStatsResponse,
    SystemLogLevelResponse,
    SystemLogLevelUpdate,
    SystemLogNameRequest,
    SystemLogClearResponse,
)
from app.services.admin_service import AdminService
from app.services.log_viewer_service import LogViewerService
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
    tencent_db: AsyncSession = Depends(get_tencent_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    data = await AdminService.get_overview(db, tencent_db=tencent_db)
    return StatsOverview(**data)


@router.get("/stats/timeseries", response_model=TimeSeriesStats)
async def get_stats_timeseries(
    period: str = Query("day", pattern="^(day|week|month|year)$"),
    db: AsyncSession = Depends(get_db),
    tencent_db: AsyncSession = Depends(get_tencent_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    data = await AdminService.get_timeseries_stats(db, period, tencent_db=tencent_db)
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
    tencent_db: AsyncSession = Depends(get_tencent_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    total, items = await AdminService.list_users(db, tencent_db=tencent_db, skip=skip, limit=limit, search=search)
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


# ---------------------------------------------------------------------------
# System logs（应用运行日志在线查看；与操作审计 /logs 不同）
# ---------------------------------------------------------------------------
@router.get("/system-logs/files", response_model=SystemLogFileListResponse)
async def list_system_log_files(
    current_user: User = Depends(get_current_user),
):
    """列出可在线查看的应用日志文件（app.log 及按天滚动副本）。"""
    _check_admin(current_user)
    return SystemLogFileListResponse(
        files=[SystemLogFileItem.model_validate(f) for f in LogViewerService.list_files()]
    )


@router.get("/system-logs/content", response_model=SystemLogContentResponse)
async def read_system_log_content(
    name: str = Query(..., description="日志文件名，如 app.log"),
    lines: int = Query(500, ge=1, le=2000, description="返回最新 N 行"),
    level: Optional[str] = Query(None, description="按级别过滤：DEBUG/INFO/WARNING/ERROR"),
    keyword: Optional[str] = Query(None, max_length=200, description="关键词过滤（不区分大小写）"),
    current_user: User = Depends(get_current_user),
):
    """读取日志文件尾部，支持级别/关键词过滤（最新行在后）。"""
    _check_admin(current_user)
    try:
        return SystemLogContentResponse(**LogViewerService.read_tail(
            name=name, lines=lines, level=level, keyword=keyword,
        ))
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日志文件不存在")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/system-logs/download")
async def download_system_log(
    name: str = Query(..., description="日志文件名，如 app.log"),
    current_user: User = Depends(get_current_user),
):
    """下载完整日志文件（管理员排障用）。"""
    _check_admin(current_user)
    try:
        path = LogViewerService.resolve_log_file(name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日志文件不存在")
    encoded_name = quote(name, safe="")
    return FileResponse(
        path=path,
        media_type="text/plain; charset=utf-8",
        filename=name,
        headers={"Content-Disposition": f'attachment; filename="{encoded_name}"'},
    )


@router.get("/system-logs/stats", response_model=SystemLogStatsResponse)
async def get_system_log_stats(
    current_user: User = Depends(get_current_user),
):
    """日志概览：各文件的 ERROR/WARNING 计数 + 当前生效的日志级别。"""
    _check_admin(current_user)
    return SystemLogStatsResponse(
        files=[SystemLogFileStats.model_validate(f) for f in LogViewerService.get_stats()],
        log_level=LogViewerService.get_log_level(),
    )


@router.get("/system-logs/level", response_model=SystemLogLevelResponse)
async def get_system_log_level(
    current_user: User = Depends(get_current_user),
):
    """当前生效的日志级别（可能是运行时调整过的，与 .env 不一定一致）。"""
    _check_admin(current_user)
    return SystemLogLevelResponse(level=LogViewerService.get_log_level())


@router.post("/system-logs/level", response_model=SystemLogLevelResponse)
async def set_system_log_level(
    payload: SystemLogLevelUpdate,
    current_user: User = Depends(get_current_user),
):
    """运行时调整全局日志级别（立即生效，重启后回退到 .env 的 LOG_LEVEL）。"""
    _check_admin(current_user)
    try:
        level = LogViewerService.set_log_level(payload.level)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return SystemLogLevelResponse(level=level)


@router.post("/system-logs/clear", response_model=SystemLogClearResponse)
async def clear_system_log(
    payload: SystemLogNameRequest,
    current_user: User = Depends(get_current_user),
):
    """清空指定日志文件内容（truncate，保留文件句柄）。"""
    _check_admin(current_user)
    try:
        cleared = LogViewerService.clear_log(payload.name)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日志文件不存在")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return SystemLogClearResponse(name=payload.name, cleared_bytes=cleared)


@router.delete("/system-logs/{name}")
async def delete_system_log_file(
    name: str,
    current_user: User = Depends(get_current_user),
):
    """删除历史滚动日志文件（app.log 当前文件只允许清空，不可删除）。"""
    _check_admin(current_user)
    try:
        LogViewerService.delete_log(name)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日志文件不存在")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"message": f"已删除 {name}"}
