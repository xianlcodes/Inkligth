import logging
from typing import Optional
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
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
    SystemLogFileStats,
    SystemLogContentResponse,
    SystemLogStatsResponse,
    SystemLogLevelResponse,
    SystemLogLevelUpdate,
    SystemLogNameRequest,
    SystemLogClearResponse,
)
from app.services.admin_service import AdminService
from app.services.log_viewer_service import LogViewerService
from app.services.platform_config_service import PlatformConfigService, SECRET_KEY_NAME
from app.models.recall_email_log import RecallEmailLog
from app.services.email_service import _send_email
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
    # 平台 Key 属于机密：即便管理员可见也只回掩码，明文永不出库
    out = []
    for cfg in items:
        item = SystemConfigItem.model_validate(cfg)
        if cfg.key == SECRET_KEY_NAME:
            item.value = PlatformConfigService.mask_config_value(SECRET_KEY_NAME, cfg.value) or ""
        out.append(item)
    return SystemConfigListResponse(items=out)


@router.post("/config", response_model=SystemConfigItem, status_code=status.HTTP_201_CREATED)
async def create_config(
    data: SystemConfigCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_admin(current_user)
    data_dict = data.model_dump(exclude={"key"})
    if data.key == SECRET_KEY_NAME:
        normalized = PlatformConfigService.normalize_incoming_secret(data.key, data_dict.get("value"))
        data_dict["value"] = normalized
    cfg = await AdminService.upsert_config(
        db, key=data.key, data=data_dict, updated_by=current_user.email,
    )
    await AdminService.create_change_log(
        db, data.key, None,
        PlatformConfigService.mask_config_value(data.key, cfg.value), current_user.email,
    )
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

    data_dict = data.model_dump(exclude_unset=True)
    if key == SECRET_KEY_NAME:
        normalized = PlatformConfigService.normalize_incoming_secret(key, data_dict.get("value"))
        data_dict["value"] = normalized
    cfg = await AdminService.upsert_config(
        db, key=key, data=data_dict, updated_by=current_user.email,
    )
    if old_val != cfg.value:
        # 审计日志同样掩码化，机密明文绝不入库
        await AdminService.create_change_log(
            db, key,
            PlatformConfigService.mask_config_value(key, old_val),
            PlatformConfigService.mask_config_value(key, cfg.value),
            current_user.email,
        )
    await AdminService.create_log(
        db, user_id=str(current_user.id), user_email=current_user.email,
        action="update_config", resource="system_config", resource_id=key,
        detail=f"Updated config {key}: {PlatformConfigService.mask_config_value(key, cfg.value) or ''}",
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


class RecallSendRequest(BaseModel):
    recall_type: str
    user_ids: list[str]


@router.post("/recall-emails/send")
async def send_recall_emails_manually(
    payload: RecallSendRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """管理员手动向指定用户发送召回邮件（不受每日自动开关限制，仍防重）。"""
    _check_admin(current_user)
    from app.tasks.recall_email import RECALL_TYPES, render_recall_email

    if payload.recall_type not in RECALL_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未知的召回类型")
    user_ids = list(dict.fromkeys(uid for uid in payload.user_ids if uid))[:200]
    if not user_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择至少一位用户")

    import asyncio
    from app.services.email_service import _send_email as _sync_send

    subject, html, text = await render_recall_email(payload.recall_type)
    sent, failed, errors = 0, 0, []
    try:
        for uid in user_ids:
            try:
                user = await UserService.get_user_by_id(db, uid)
                if not user or not getattr(user, "email", None):
                    failed += 1
                    errors.append(f"{uid}: 无邮箱或用户不存在")
                    continue
                ok, msg = await asyncio.to_thread(_sync_send, user.email, subject, html, text)
                if ok:
                    db.add(RecallEmailLog(user_id=str(user.id), recall_type=payload.recall_type))
                    await db.commit()
                    sent += 1
                else:
                    failed += 1
                    errors.append(f"{user.email}: {msg[:80]}")
            except Exception as e:
                failed += 1
                errors.append(f"{uid}: {str(e)[:80]}")

        await AdminService.create_log(
            db, user_id=str(current_user.id), user_email=current_user.email,
            action="send_recall_email", resource="recall_email", resource_id=payload.recall_type,
            detail=f"手动发送召回邮件 type={payload.recall_type} sent={sent} failed={failed}",
            ip_address=request.client.host if request.client else None,
        )
        await db.commit()
    except Exception as e:
        logger.error("Manual recall send failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"发送失败: {str(e)[:150]}")

    return {"sent": sent, "failed": failed, "total": len(user_ids), "errors": errors[:10]}
