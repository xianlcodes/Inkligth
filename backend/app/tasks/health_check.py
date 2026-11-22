"""每小时系统自检：主动发现依赖故障，而不是等用户请求撞上。

检查项：
- 腾讯云文献库 / 阿里云用户库连通性（SELECT 1，10 秒超时，报告耗时——
  跨云链路变慢时会先在这里暴露，而不是让用户请求排队 30 秒）
- Redis（「未启用」属已接受的降级状态只记 INFO；曾在用但探测失败才记异常）
- 磁盘剩余空间（低于 2GB 告警，影响上传与日志写入）
- 日志目录可写

结果：全部通过记一条 INFO 汇总；任何一项失败记 ERROR 汇总——管理页
「概览统计」的 ERROR 计数即可当作巡检失败次数。由 app/tasks/scheduler.py
每小时调度一次，启动 60 秒后先跑第一轮。
"""
import asyncio
import logging
import shutil
import time
from pathlib import Path

from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger("inklight.health")

_DISK_MIN_FREE_GB = 2.0
_DB_CHECK_TIMEOUT_S = 10


async def _check_db(engine, name: str) -> tuple[bool, str]:
    start = time.perf_counter()

    async def _ping():
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(_ping(), timeout=_DB_CHECK_TIMEOUT_S)
        ms = (time.perf_counter() - start) * 1000
        return True, f"{name}正常({ms:.0f}ms)"
    except asyncio.TimeoutError:
        return False, f"{name}连接超时(>{_DB_CHECK_TIMEOUT_S}s)"
    except Exception as e:
        return False, f"{name}连接失败: {type(e).__name__}: {str(e)[:120]}"


async def _check_redis() -> tuple[bool, str]:
    from app.core.redis import redis_manager

    if not redis_manager.available:
        # 已知的降级基线（当前生产未部署 Redis，任务状态走内存），不算故障
        return True, "未启用（内存模式运行，任务状态重启后丢失）"
    try:
        await asyncio.wait_for(
            redis_manager.setex("health_probe", 10, "1"), timeout=_DB_CHECK_TIMEOUT_S
        )
        value = await asyncio.wait_for(
            redis_manager.get("health_probe"), timeout=_DB_CHECK_TIMEOUT_S
        )
        if value == "1":
            return True, "读写正常"
        return False, "探测写入后读取结果不符（可能被其它进程干扰）"
    except Exception as e:
        # 之前可用、现在探测失败：状态劣化，必须告警
        return False, f"曾在用但探测失败: {type(e).__name__}: {str(e)[:120]}"


def _check_disk() -> tuple[bool, str]:
    try:
        log_dir = Path(settings.LOG_DIR)
        target = log_dir if log_dir.is_dir() else Path(".")
        free_gb = shutil.disk_usage(target).free / 1024**3
        if free_gb < _DISK_MIN_FREE_GB:
            return False, f"磁盘剩余仅 {free_gb:.1f}GB（低于 {_DISK_MIN_FREE_GB}GB，可能影响上传与日志写入）"
        return True, f"磁盘剩余 {free_gb:.0f}GB"
    except Exception as e:
        return False, f"磁盘检查失败: {e}"


def _check_log_writable() -> tuple[bool, str]:
    probe = Path(settings.LOG_DIR) / ".health_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True, "日志目录可写"
    except Exception as e:
        return False, f"日志目录不可写: {e}"


async def run_health_check() -> None:
    """执行一轮自检并汇总；由调度器每小时调用。"""
    from app.db.database import tencent_engine, alibaba_engine

    start = time.perf_counter()

    checks: list[tuple[bool, str]] = []

    ok, msg = await _check_db(tencent_engine, "文献库")
    checks.append((ok, f"文献库: {msg}"))
    logger.info("自检 · 文献库(腾讯): %s", msg)

    ok, msg = await _check_db(alibaba_engine, "用户库")
    checks.append((ok, f"用户库: {msg}"))
    logger.info("自检 · 用户库(阿里): %s", msg)

    ok, msg = await _check_redis()
    checks.append((ok, f"Redis: {msg}"))
    logger.info("自检 · Redis: %s", msg)

    ok, msg = _check_disk()
    checks.append((ok, msg))
    if not ok:
        logger.error("自检 · 磁盘: %s", msg)

    ok, msg = _check_log_writable()
    checks.append((ok, msg))
    if not ok:
        logger.error("自检 · 日志目录: %s", msg)

    failures = [msg for ok, msg in checks if not ok]
    elapsed_ms = (time.perf_counter() - start) * 1000

    if failures:
        logger.error(
            "系统自检失败：%s（耗时 %.0fms）", "；".join(failures), elapsed_ms
        )
    else:
        logger.info(
            "系统自检通过：%s（耗时 %.0fms）",
            "；".join(msg for _, msg in checks), elapsed_ms,
        )
