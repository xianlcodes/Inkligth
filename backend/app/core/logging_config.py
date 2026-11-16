"""应用日志配置：统一格式、双输出（stdout + 按天轮转文件）、北京时间时间戳。

在 main.py 顶部调用一次 setup_logging() 即可；幂等，重复调用直接返回。

设计要点：
- 根级别由 settings.LOG_LEVEL 控制（默认 INFO），业务代码里大量的
  logger.info（任务创建、AI 调用、翻译进度）由此变为可见；
- 文件日志写入 settings.LOG_DIR/app.log，按天滚动，保留
  settings.LOG_RETENTION_DAYS 天，配合生产挂载卷实现发版后日志不丢；
- 时间戳转为北京时间（固定偏移，不依赖容器系统 tzdata，容器默认 UTC）；
- request_id 由 app/core/request_context.py 的 RequestIdFilter 注入
  每条日志（挂在 handler 上，对全部子 logger 的传播记录生效）。
"""
import logging
import logging.handlers
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import settings
from app.core.request_context import RequestIdFilter

logger = logging.getLogger(__name__)

# 统一日志格式；request_id 由 RequestIdFilter 填充，非请求上下文为 "-"
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | [%(request_id)s] | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 第三方库降噪：这些 logger 保持 WARNING，避免淹没业务日志
_THIRD_PARTY_WARNING = ("sqlalchemy", "httpx", "httpcore", "urllib3")
# 业务代码里日志量偏大的模块，维持原有 WARNING 静音（main.py 旧逻辑保留）
_APP_WARNING = (
    "app.core.ai_providers.provider_registry",
    "app.services.layout_analysis_service",
)

_configured = False

# 数据库连接串脱敏：postgresql+asyncpg://user:password@host:port/db
_DB_URL_PASSWORD_PATTERN = re.compile(r"(?<=://)([^:@/]+):([^@]+)(?=@)")


def mask_db_url(url: str) -> str:
    """掩去数据库连接串里的密码，避免明文密码落进日志文件。"""
    if not url:
        return url
    return _DB_URL_PASSWORD_PATTERN.sub(r"\1:***", url)


class _TZFormatter(logging.Formatter):
    """时间戳按指定 UTC 偏移输出（默认北京时间），不依赖系统 tzdata。"""

    def __init__(self, fmt: str, datefmt: str, utc_offset_hours: float):
        super().__init__(fmt, datefmt)
        self._tz = timezone(timedelta(hours=utc_offset_hours))

    def formatTime(self, record: logging.LogRecord, datefmt=None) -> str:  # noqa: N802
        dt = datetime.fromtimestamp(record.created, self._tz)
        return dt.strftime(datefmt or self.datefmt)


def setup_logging() -> None:
    """初始化全局日志。仅 main.py 顶部调用一次。"""
    global _configured
    if _configured:
        return
    _configured = True

    level_name = (getattr(settings, "LOG_LEVEL", "INFO") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    log_dir = Path(getattr(settings, "LOG_DIR", "logs"))
    retention = int(getattr(settings, "LOG_RETENTION_DAYS", 14))
    utc_offset = float(getattr(settings, "LOG_UTC_OFFSET_HOURS", 8.0))

    # 清掉已有 handler（uvicorn 等可能预先配置过），避免重复输出
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    formatter = _TZFormatter(LOG_FORMAT, LOG_DATE_FORMAT, utc_offset)
    request_filter = RequestIdFilter()

    # 1) stdout：docker logs 兼容
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.addFilter(request_filter)
    root.addHandler(console)

    # 2) 按天轮转文件：发版/重启不丢历史；目录不可写时仅告警，不影响启动
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_dir / "app.log",
            when="midnight",
            backupCount=retention,
            encoding="utf-8",
            delay=True,
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(request_filter)
        root.addHandler(file_handler)
    except Exception as e:
        logger.warning("日志文件初始化失败（仅输出到 stdout）：%s", e)

    root.setLevel(level)

    # 第三方降噪；sqlalchemy 保持 WARNING 但允许传播，DB 报错可见（不打 SQL）
    for name in _THIRD_PARTY_WARNING:
        logging.getLogger(name).setLevel(logging.WARNING)
    for name in _APP_WARNING:
        logging.getLogger(name).setLevel(logging.WARNING)
    # uvicorn：访问日志由 request_context 中间件承担（带 request_id/耗时/用户），
    # error logger 提到 INFO 让启动信息可见
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
