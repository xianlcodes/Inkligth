"""日志文件查看服务：供管理端在线检索 LOG_DIR 下的应用日志。

安全边界：
- 文件名只允许匹配 _LOG_FILE_PATTERN 白名单（app.log 及按天滚动的
  app.log.YYYY-MM-DD），彻底杜绝路径穿越；
- 读尾部而非全量读取，单次最多读 _MAX_READ_BYTES，防止大文件拖垮内存；
- 返回行数有上限，关键词/级别过滤在内存中完成。
"""
import logging
import re
from datetime import datetime
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# 允许查看的日志文件名白名单（app.log 与按天滚动的副本）
_LOG_FILE_PATTERN = re.compile(r"^app\.log(\.\d{4}-\d{2}-\d{2})?$")

_MAX_READ_BYTES = 1024 * 1024          # 单次最多从文件读取 1MB
_MAX_RETURN_LINES = 2000               # 单次最多返回行数
_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

# 日志行示例：2026-11-07 10:20:30 | WARNING | app.core.translator | [abc] | msg
_LINE_LEVEL_PATTERN = re.compile(r"\|\s*(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*\|")


class LogViewerService:
    @staticmethod
    def _log_dir() -> Path:
        return Path(settings.LOG_DIR)

    @staticmethod
    def list_files() -> list[dict]:
        """列出白名单内的日志文件，按修改时间倒序。"""
        log_dir = LogViewerService._log_dir()
        if not log_dir.is_dir():
            return []
        files: list[dict] = []
        for entry in log_dir.iterdir():
            if not entry.is_file() or not _LOG_FILE_PATTERN.match(entry.name):
                continue
            stat = entry.stat()
            files.append({
                "name": entry.name,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime),
            })
        files.sort(key=lambda f: f["modified_at"], reverse=True)
        return files

    @staticmethod
    def resolve_log_file(name: str) -> Path:
        """校验文件名并返回绝对路径；不合法直接拒绝。"""
        if not name or not _LOG_FILE_PATTERN.match(name):
            raise ValueError(f"非法的日志文件名: {name!r}")
        path = (LogViewerService._log_dir() / name).resolve()
        # 双保险：解析后必须仍位于日志目录内
        if not str(path).startswith(str(LogViewerService._log_dir().resolve())):
            raise ValueError(f"非法的日志文件名: {name!r}")
        return path

    @staticmethod
    def read_tail(
        name: str,
        lines: int = 500,
        level: str | None = None,
        keyword: str | None = None,
    ) -> dict:
        """读取日志文件尾部，可按级别/关键词过滤，最新行在后。

        行数/关键词过大时在参数层截断；文件不存在抛 FileNotFoundError。
        """
        path = LogViewerService.resolve_log_file(name)
        lines = max(1, min(int(lines or 500), _MAX_RETURN_LINES))
        level_up = (level or "").strip().upper() or None
        if level_up and level_up not in _VALID_LEVELS:
            raise ValueError(f"非法的日志级别: {level!r}")
        keyword = (keyword or "").strip()[:200] or None

        if not path.is_file():
            raise FileNotFoundError(name)

        with open(path, "rb") as f:
            f.seek(0, 2)
            total_size = f.tell()
            f.seek(max(0, total_size - _MAX_READ_BYTES))
            chunk = f.read(_MAX_READ_BYTES).decode("utf-8", errors="replace")

        # 丢掉可能被截断的首行
        raw_lines = chunk.splitlines()
        if total_size > _MAX_READ_BYTES and raw_lines:
            raw_lines = raw_lines[1:]

        total_lines = len(raw_lines)
        matched: list[str] = []
        for line in raw_lines:
            if level_up:
                m = _LINE_LEVEL_PATTERN.search(line)
                if not m or m.group(1) != level_up:
                    continue
            if keyword and keyword.lower() not in line.lower():
                continue
            matched.append(line)

        truncated = len(matched) > lines
        return {
            "name": name,
            "total_lines": total_lines,
            "returned_lines": min(len(matched), lines),
            "truncated": truncated,
            "lines": matched[-lines:],
        }

    # ------------------------------------------------------------------
    # 日志管理：概览统计 / 运行时调级 / 清空 / 删除
    # ------------------------------------------------------------------
    @staticmethod
    def get_stats() -> list[dict]:
        """逐文件统计 ERROR/WARNING 行数（配合 list_files 的元数据）。"""
        result = []
        for f in LogViewerService.list_files():
            error_count = warning_count = 0
            try:
                path = LogViewerService.resolve_log_file(f["name"])
                with open(path, "r", encoding="utf-8", errors="replace") as fp:
                    for line in fp:
                        m = _LINE_LEVEL_PATTERN.search(line)
                        if not m:
                            continue
                        if m.group(1) in ("ERROR", "CRITICAL"):
                            error_count += 1
                        elif m.group(1) == "WARNING":
                            warning_count += 1
            except OSError as e:
                logger.warning("统计日志文件失败 %s: %s", f["name"], e)
            result.append({
                "name": f["name"],
                "size_bytes": f["size_bytes"],
                "modified_at": f["modified_at"],
                "error_count": error_count,
                "warning_count": warning_count,
            })
        return result

    @staticmethod
    def get_log_level() -> str:
        return logging.getLevelName(logging.getLogger().getEffectiveLevel())

    @staticmethod
    def set_log_level(level: str) -> str:
        """运行时调整根日志级别，立即生效；重启后回退到 .env 的 LOG_LEVEL。"""
        level_up = (level or "").strip().upper()
        if level_up not in _VALID_LEVELS:
            raise ValueError(f"非法的日志级别: {level!r}")
        logging.getLogger().setLevel(getattr(logging, level_up))
        logger.info(
            "管理员将日志级别调整为 %s（运行时生效，重启后回退到 .env 的 LOG_LEVEL）",
            level_up,
        )
        return level_up

    @staticmethod
    def clear_log(name: str) -> int:
        """清空日志文件内容（truncate），返回清空的字节数。"""
        path = LogViewerService.resolve_log_file(name)
        if not path.is_file():
            raise FileNotFoundError(name)
        size = path.stat().st_size
        # r+b 截断而非删除：TimedRotatingFileHandler 持有文件句柄，
        # 删除后它会继续写入已被 unlink 的 inode，日志会"消失"
        with open(path, "r+b") as fp:
            fp.truncate(0)
        logger.warning("管理员清空了日志文件 %s（释放 %d 字节）", name, size)
        return size

    @staticmethod
    def delete_log(name: str) -> None:
        """删除历史滚动日志文件。当前正在写入的 app.log 只允许清空。"""
        if name == "app.log":
            raise ValueError(
                "当前日志文件 app.log 正在被写入，只能清空，不能删除"
            )
        path = LogViewerService.resolve_log_file(name)
        if not path.is_file():
            raise FileNotFoundError(name)
        path.unlink()
        logger.warning("管理员删除了日志文件 %s", name)
