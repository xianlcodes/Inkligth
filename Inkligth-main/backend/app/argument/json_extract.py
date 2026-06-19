"""从 LLM 响应中提取 JSON — 三阶段算法

直接移植自 scholar-assistant-agent-main/src/utils/json_extract.py

阶段：
  1. 直接 json.loads
  2. 去除 Markdown 围栏（```json ... ```）后解析
  3. 平衡括号扫描（在任意位置找到第一个 { 或 [，配对闭合符号）
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```(?:[a-zA-Z]*)\s*\n(.*?)\n\s*```", re.DOTALL)


def _skip_string(text: str, start: int, quote: str) -> int:
    """跳过 JSON 字符串内容，返回结束引号后的位置"""
    i = start + 1
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2  # 跳过转义序列
            continue
        if ch == quote:
            return i + 1
        i += 1
    return i


def _balanced_scan(text: str, start: int, open_ch: str, close_ch: str) -> int | None:
    """从 start 开始，找到与 open_ch 匹配的 close_ch 位置（考虑嵌套和字符串）"""
    depth = 1
    i = start + 1
    while i < len(text):
        ch = text[i]
        if ch in ('"', "'"):
            i = _skip_string(text, i, ch)
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def _try_loads(s: str) -> dict | list | None:
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return None


def extract_json_object(text: str) -> dict | None:
    """从 LLM 响应中提取第一个 JSON 对象，失败返回 None"""
    result = _extract(text, "{", "}")
    if isinstance(result, dict):
        return result
    return None


def extract_json_array(text: str) -> list | None:
    """从 LLM 响应中提取第一个 JSON 数组，失败返回 None"""
    result = _extract(text, "[", "]")
    if isinstance(result, list):
        return result
    return None


def _extract(text: str, open_ch: str, close_ch: str) -> dict | list | None:
    """三阶段 JSON 提取"""
    if not text or not text.strip():
        return None

    original = text.strip()

    # 阶段 1: 直接解析
    result = _try_loads(original)
    if result is not None:
        return result

    # 阶段 2: 去除 Markdown 围栏
    m = _FENCE_RE.search(original)
    if m:
        result = _try_loads(m.group(1).strip())
        if result is not None:
            return result

    # 阶段 3: 平衡括号扫描
    start = original.find(open_ch)
    while start != -1:
        end = _balanced_scan(original, start, open_ch, close_ch)
        if end is not None:
            candidate = original[start:end]
            result = _try_loads(candidate)
            if result is not None:
                return result
        start = original.find(open_ch, start + 1)

    return None
