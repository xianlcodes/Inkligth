"""
锚点系统 - 将引文定位/重定位到 PDF 原文

支持精确匹配、上下文辅助匹配、模糊匹配三种策略。
"""

import difflib
import json
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class AnchorStatus(str, Enum):
    ANCHORED = "anchored"
    DRIFTED = "drifted"
    LOST = "lost"


class AnchorResult:
    """锚点定位结果"""
    def __init__(
        self,
        status: AnchorStatus,
        quote: str,
        char_start: Optional[int] = None,
        char_end: Optional[int] = None,
        context_before: str = "",
        context_after: str = "",
        section: str = "",
        confidence: float = 1.0,
    ):
        self.status = status
        self.quote = quote
        self.char_start = char_start
        self.char_end = char_end
        self.context_before = context_before
        self.context_after = context_after
        self.section = section
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "quote": self.quote,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "section": self.section,
            "confidence": self.confidence,
        }


def locate_quote(
    full_text: str,
    quote: str,
    context_before: str = "",
    context_after: str = "",
    fuzzy_threshold: float = 0.62,
) -> AnchorResult:
    """在全文中的定位引文位置

    支持 4 级定位策略：
    1. 精确匹配
    2. 上下文辅助匹配
    3. 模糊匹配（difflib）
    4. 失败 -> LOST

    Args:
        full_text: 论文全文
        quote: 需要定位的引文
        context_before: 前文（辅助定位）
        context_after: 后文（辅助定位）
        fuzzy_threshold: 模糊匹配阈值（0.0-1.0）

    Returns:
        AnchorResult
    """
    if not full_text or not quote:
        return AnchorResult(AnchorStatus.LOST, quote, confidence=0.0)

    # 策略 1: 精确匹配
    idx = full_text.find(quote)
    if idx != -1:
        logger.debug("Exact match found at position %d", idx)
        before = full_text[max(0, idx - 100):idx]
        after = full_text[idx + len(quote):idx + len(quote) + 100]
        section = _detect_section(full_text, idx)
        return AnchorResult(
            status=AnchorStatus.ANCHORED,
            quote=quote,
            char_start=idx,
            char_end=idx + len(quote),
            context_before=before,
            context_after=after,
            section=section,
            confidence=1.0,
        )

    # 策略 2: 上下文辅助匹配
    if context_before or context_after:
        combined_context = ""
        if context_before:
            combined_context = context_before[-200:] + quote[:50]
        if context_after:
            combined_context = quote[-50:] + context_after[:200]

        if combined_context:
            ctx_idx = full_text.find(combined_context[:100])
            if ctx_idx != -1:
                search_region = full_text[ctx_idx:ctx_idx + len(combined_context) + 500]
                q_idx = search_region.find(quote)
                if q_idx != -1:
                    actual_pos = ctx_idx + q_idx
                    before = full_text[max(0, actual_pos - 100):actual_pos]
                    after = full_text[actual_pos + len(quote):actual_pos + len(quote) + 100]
                    section = _detect_section(full_text, actual_pos)
                    logger.debug("Context-assisted match at position %d", actual_pos)
                    return AnchorResult(
                        status=AnchorStatus.ANCHORED,
                        quote=quote,
                        char_start=actual_pos,
                        char_end=actual_pos + len(quote),
                        context_before=before,
                        context_after=after,
                        section=section,
                        confidence=0.95,
                    )

    # 策略 3: 模糊匹配
    words = quote.split()
    if len(words) >= 3:
        segments = [
            " ".join(words[:3]),
            " ".join(words[len(words)//2:len(words)//2+3]),
            " ".join(words[-3:]),
        ]

        positions = []
        for seg in segments:
            matches = _fuzzy_find(full_text, seg, threshold=fuzzy_threshold)
            for pos, ratio in matches:
                positions.append((pos, ratio))

        if positions:
            positions.sort(key=lambda x: -x[1])
            best_pos = positions[0][0]

            window = full_text[best_pos:best_pos + len(quote) + 200]
            q_idx = window.find(quote[:50])
            if q_idx == -1:
                before = full_text[max(0, best_pos - 100):best_pos]
                after = full_text[best_pos + len(quote):best_pos + len(quote) + 100]
                section = _detect_section(full_text, best_pos)
                logger.debug("Fuzzy match at position %d (confidence=%.2f)", best_pos, positions[0][1])
                return AnchorResult(
                    status=AnchorStatus.DRIFTED,
                    quote=quote,
                    char_start=best_pos,
                    char_end=best_pos + len(quote),
                    context_before=before,
                    context_after=after,
                    section=section,
                    confidence=positions[0][1],
                )

    logger.debug("Quote not found in text: %.60s...", quote)
    return AnchorResult(AnchorStatus.LOST, quote, confidence=0.0)


def _fuzzy_find(text: str, pattern: str, threshold: float = 0.62) -> list[tuple[int, float]]:
    """在文本中模糊查找模式，返回 (位置, 相似度) 列表"""
    results = []
    pattern_len = len(pattern)
    step = max(pattern_len // 2, 1)

    for i in range(0, max(len(text) - pattern_len + 1, 1), step):
        chunk = text[i:i + pattern_len]
        ratio = difflib.SequenceMatcher(None, pattern, chunk).ratio()
        if ratio >= threshold:
            results.append((i, ratio))

    if results:
        results.sort(key=lambda x: -x[1])
        deduped = [results[0]]
        for pos, ratio in results[1:]:
            if abs(pos - deduped[-1][0]) > pattern_len:
                deduped.append((pos, ratio))
        return deduped

    return []


def _detect_section(full_text: str, position: int) -> str:
    """检测位置所在的章节标题"""
    before = full_text[:position]
    lines = before.split("\n")
    for line in reversed(lines[-30:]):
        line = line.strip()
        if line and (
            line.startswith("#") or
            line.startswith("##") or
            line.startswith("###") or
            line.isupper() or
            any(line.lower().startswith(prefix) for prefix in
                ["abstract", "introduction", "method", "experiment",
                 "result", "discussion", "conclusion", "reference"])
        ):
            return line[:100]
    return "unknown"
