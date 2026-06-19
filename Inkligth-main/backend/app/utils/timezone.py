"""
时区工具 —— 统一使用北京时间（Asia/Shanghai）
"""

from datetime import datetime, timezone, timedelta
import zoneinfo

BJT = zoneinfo.ZoneInfo("Asia/Shanghai")
"""北京时区对象"""


def now_bjt() -> datetime:
    """返回当前北京时间（带时区信息）"""
    return datetime.now(BJT)


def utc_to_bjt(dt: datetime) -> datetime:
    """将 UTC datetime 转换为北京时间（自动处理 naive/aware）"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BJT)


def bjt_to_utc(dt: datetime) -> datetime:
    """将北京时间转换为 UTC（返回 naive UTC）"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJT)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)
