"""承诺台账 (Ledger) 核心逻辑（异步）

双 LLM 流水线：
  1. extract_promises  — 从 Abstract / Introduction 提取承诺
  2. check_discharge   — 对照 Methods / Experiments / Results 检查兑现
  3. anchor_quotes     — 用 anchor.py 定位引文
  4. SSE 流式推送

严格参考 scholar-assistant-agent-main/python/src/argument/ledger.py 的实现：
  - _extract_promise_zone 区域提取
  - extract_json_object / extract_json_array（3 阶段 JSON 解析）
  - 2 次 LLM 调用重试
  - 逐个承诺兑现检查
  - _STATUS_SEVERITY 映射

每个步骤均以 async generator 形式输出事件，供 router 层 SSE 转发。
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional

from app.argument.anchor import locate_quote
from app.argument.json_extract import extract_json_array, extract_json_object

logger = logging.getLogger(__name__)


# ── Data types ──


@dataclass
class ExtractedPromise:
    """LLM 提取的单条承诺"""
    claim_text: str
    severity: str = "info"           # info | warning | error
    status: str = "unpaid"           # unpaid | partial | paid | mismatch
    section_hint: str = ""
    discharge_text: str = ""
    confidence: float = 0.8


@dataclass
class LedgerBuildEvent:
    """构建过程的 SSE 事件"""
    event: str                       # progress | promise_extracted | promise_checked | anchored | complete | error
    data: dict = field(default_factory=dict)


# ── Section extraction（移植自 reference project）──

_PROMISE_SECTION_RE = re.compile(
    r"^#{1,3}\s*(abstract|摘要|introduction|引言|研究背景|研究动机|intro|background|motivation)\b",
    re.IGNORECASE | re.MULTILINE,
)
_METHOD_RE = re.compile(
    r"^#{1,3}\s*(method|approach|methodology|方法|实验|experiment|3\s|4\s)\b",
    re.IGNORECASE | re.MULTILINE,
)
_HEADER_RE = re.compile(r"^#{1,3}\s+", re.MULTILINE)


def _extract_promise_zone(text: str, max_promise_chars: int = 6000) -> tuple[str, str]:
    """将文本分为 (承诺区域, 正文区域)

    承诺区域：从开头到 methods/approach 章节之前（含摘要、引言、动机、相关工作等）
    正文区域：methods/approach 及之后的内容（实验、结果等）

    等价于参考项目的同名函数。
    """
    if not text:
        return "", ""

    m_method = _METHOD_RE.search(text)
    if m_method:
        return text[:m_method.start()], text[m_method.start():]

    m = _PROMISE_SECTION_RE.search(text)
    if not m:
        cut = min(len(text), max_promise_chars)
        return text[:cut], text[cut:]

    start = m.start()
    for h in _HEADER_RE.finditer(text, m.end()):
        if _METHOD_RE.search(h.group()):
            return text[start:h.start()], text[h.start():]

    cut = min(len(text), max(max_promise_chars, len(text) * 2 // 5))
    return text[:cut], text[cut:]


# ── Body sampling（移植自 reference project）──

def _extract_section(full_text: str, section_keyword: str, max_chars: int = 3000) -> str:
    """从全文中提取特定章节内容"""
    if not full_text:
        return ""

    text_lower = full_text.lower()
    keywords = {
        "abstract": ["abstract", "摘要"],
        "introduction": ["introduction", "引言", "介绍", "背景"],
        "method": ["method", "approach", "framework", "proposed", "方法", "框架", "算法"],
        "experiment": ["experiment", "evaluation", "empirical", "实验", "评估"],
        "result": ["result", "finding", "discussion", "结果", "讨论"],
    }

    search_terms = keywords.get(section_keyword, [section_keyword])
    positions = []
    for term in search_terms:
        idx = text_lower.find(term)
        if idx != -1:
            positions.append(idx)

    if not positions:
        return ""

    start = min(positions)
    end = start + max_chars
    return full_text[start:end]


# ── Body sampling（移植自 reference project）──

def _sample_body(body: str, total: int = 8000) -> str:
    """采样正文：首段 + 中段 + 末段，避免超长截断"""
    if len(body) <= total:
        return body
    chunk = total // 3
    mid = len(body) // 2
    return (
        body[:chunk]
        + f"\n\n[... 中间省略 {mid - chunk} 字符 ...]\n\n"
        + body[mid - chunk // 2: mid + chunk // 2]
        + f"\n\n[... 省略至末尾 ...]\n\n"
        + body[-chunk:]
    )


# ── Status severity mapping（移植自 reference project）──

_STATUS_SEVERITY = {
    "unpaid": "error",
    "mismatch": "error",
    "partial": "warning",
    "paid": "info",
    "unknown": "info",
}


# ── Prompt templates（移植自 reference project）──

EXTRACT_PROMPT = """你是学术论证分析专家。从这篇论文的前半部分（摘要、引言、动机、研究背景等）全面提取作者立下的所有承诺。

承诺类型说明：
- contribution: 具体贡献声明（'我们提出了…'、'本文的贡献包括…'）
- claim: 学术主张或断言（'X 优于 Y'、'该方法能解决…'）
- hypothesis: 待验证假设（'我们假设…'、'预期…'）
- gap_statement: 指出的研究空白（'现有方法未解决…'、'缺乏…'）
- scope: 范围限定或边界声明（'本文聚焦于…'、'不包括…'）

请仔细阅读全文，不要遗漏。一篇论文通常有 5-15 条承诺，分布在多个段落中。
特别注意：贡献列表、'we propose'、'we demonstrate'、'our approach'、'主要创新'、
'本文旨在'、'与现有方法不同'等表述都应提取。

文本：
{text}

输出严格 JSON（不含其他文字）：
{{"promises":[{{"local_id":"p1","kind":"contribution","text":"承诺原话(可适度归一)","verbatim_quote":"文中的精确子串"}}]}}"""

CHECK_DISCHARGE_PROMPT = """你是一位严谨的学术论文审稿人。请检查论文中的研究承诺是否在后续内容中得到兑现。

承诺原文：{claim_text}

论文内容（Methods / Experiments / Results）：
{context}

请判断该承诺的兑现状态，输出 JSON：
```json
{{
  "status": "paid | partial | unpaid | mismatch",
  "note": "判断理由（中文）：paid 时说证据在哪；unpaid/partial 时说缺什么",
  "evidence": "找到的兑现证据原文（如找到，否则留空）"
}}
```

状态定义：
- paid:  承诺在 Methods / Experiments / Results 中有明确对应的内容
- partial: 部分兑现，有相关内容但不完全
- unpaid: 完全没有兑现
- mismatch: 承诺内容与后续实现存在矛盾

请注意：
- 重点关注 Methods、Experiments、Results 等章节
- evidence 应直接引用原文
- note 请用中文说明"""


# ── Async Orchestration ──


async def extract_promises(
    full_text: str,
    literature_id: str = "",
    call_llm: Optional[callable] = None,
) -> AsyncGenerator[LedgerBuildEvent, list[ExtractedPromise]]:
    """Step 1: 从论文中提取承诺（异步流式）

    移植自 reference project 的 build_ledger 中 LLM #1 部分。
    使用 _extract_promise_zone 提取承诺区域，2 次重试，extract_json_object 解析。
    """
    full_len = len(full_text) if full_text else 0
    logger.info("extract_promises: full_text length=%d, literature_id=%s", full_len, literature_id)

    if not full_text or full_len < 50:
        logger.warning("extract_promises: full_text too short (%d chars)", full_len)
        yield LedgerBuildEvent("progress", {"step": "extract", "message": f"论文全文过短（{full_len} 字符），无法提取承诺"})
        return

    # 使用参考项目的承诺区域提取
    promise_zone, _ = _extract_promise_zone(full_text)
    pz_text = promise_zone[:6000] if len(promise_zone) > 6000 else promise_zone

    logger.info("extract_promises: promise_zone length=%d (after trim=%d)", len(promise_zone), len(pz_text))

    yield LedgerBuildEvent("progress", {"step": "extract", "message": "正在提取研究承诺..."})

    try:
        prompt = EXTRACT_PROMPT.format(text=pz_text)
        logger.info("extract_promises: calling LLM with prompt length=%d", len(prompt))

        # 2 次重试（参考项目模式）
        raw = ""
        for attempt in range(2):
            try:
                raw = await call_llm(
                    prompt if attempt == 0
                    else f"请只输出有效的 JSON 对象：\n{raw[:500]}",
                    system="你是一个严谨的学术审稿助手。",
                )
                if raw and raw.strip():
                    parsed = extract_json_object(raw)
                    if parsed is not None:
                        break
            except Exception:
                if attempt == 1:
                    yield LedgerBuildEvent("error", {"step": "extract", "message": "LLM 未返回有效 JSON，请重试"})
                    return

        if not raw or not raw.strip():
            yield LedgerBuildEvent("error", {"step": "extract", "message": "LLM 返回空响应，请重试"})
            return

        parsed1 = extract_json_object(raw)
        if not parsed1:
            yield LedgerBuildEvent("error", {"step": "extract", "message": "LLM 未返回有效 JSON，请重试"})
            return

        raw_promises = parsed1.get("promises", [])
        logger.info("extract_promises: parsed %d promises from LLM", len(raw_promises))

        promises: list[ExtractedPromise] = []
        valid_kinds = {"contribution", "claim", "hypothesis", "gap_statement", "scope"}

        for rp in raw_promises:
            kind = str(rp.get("kind", ""))
            if kind not in valid_kinds:
                logger.debug("extract_promises: skipping invalid kind=%r", kind)
                continue

            claim_text = str(rp.get("text", "")).strip()
            if not claim_text:
                logger.debug("extract_promises: skipping empty claim_text")
                continue

            # 从 kind 推断 severity
            if kind == "contribution":
                severity = "error"
            elif kind in ("claim", "hypothesis"):
                severity = "warning"
            else:
                severity = "info"

            ep = ExtractedPromise(
                claim_text=claim_text,
                severity=severity,
                section_hint=str(rp.get("kind", "")),
            )
            promises.append(ep)

            yield LedgerBuildEvent("promise_extracted", {
                "claim_text": ep.claim_text,
                "severity": ep.severity,
                "section_hint": ep.section_hint,
            })

        if not promises:
            yield LedgerBuildEvent("progress", {"step": "extract", "message": "未识别出明确的研究承诺"})
        else:
            logger.info("extract_promises: %d valid promises after filtering", len(promises))

        return

    except Exception as e:
        logger.exception("Failed to extract promises")
        yield LedgerBuildEvent("error", {"step": "extract", "message": str(e)})
        return


async def check_discharge(
    full_text: str,
    promises: list[ExtractedPromise],
    call_llm: Optional[callable] = None,
) -> AsyncGenerator[LedgerBuildEvent, list[ExtractedPromise]]:
    """Step 2: 检查每个承诺的兑现情况（异步流式）

    逐个承诺分别调用 LLM，每个承诺携带完整的 Methods/Experiments/Results 上下文。
    使用 extract_json_object 做 3 阶段 JSON 解析。
    使用 _STATUS_SEVERITY 映射严重程度。
    """
    if not promises:
        return

    # 提取 Methods/Experiments/Results 上下文
    methods = _extract_section(full_text, "method", 5000)
    experiments = _extract_section(full_text, "experiment", 5000)
    results = _extract_section(full_text, "result", 3000)
    context = f"[Methods]\n{methods}\n\n[Experiments]\n{experiments}\n\n[Results]\n{results}"

    total = len(promises)
    for i, promise in enumerate(promises):
        yield LedgerBuildEvent("progress", {
            "step": "check",
            "message": f"正在检查承诺 {i+1}/{total}...",
            "current": i + 1,
            "total": total,
        })

        if not promise.claim_text:
            continue

        try:
            prompt = CHECK_DISCHARGE_PROMPT.format(
                claim_text=promise.claim_text,
                context=context,
            )
            response = await call_llm(prompt, system="你是一个严谨的学术审稿助手。")
            result = extract_json_object(response) or {}

            status = str(result.get("status", "unpaid"))
            if status not in ("paid", "partial", "unpaid", "mismatch"):
                status = "unpaid"

            promise.status = status
            promise.severity = _STATUS_SEVERITY.get(status, "info")

            # 优先使用 note（中文说明），其次 evidence（原文引用）
            note = result.get("note", "")
            evidence = result.get("evidence", "")
            if note:
                promise.discharge_text = note
            elif evidence:
                promise.discharge_text = evidence
            else:
                promise.discharge_text = ""

            promise.confidence = 0.9 if status == "paid" else 0.7

            yield LedgerBuildEvent("promise_checked", {
                "claim_text": promise.claim_text,
                "status": promise.status,
                "discharge_text": promise.discharge_text[:200] if promise.discharge_text else "",
            })

        except Exception as e:
            logger.warning("Failed to check promise: %s", e)
            yield LedgerBuildEvent("error", {
                "step": "check",
                "claim_text": promise.claim_text,
                "message": str(e),
            })

    return


def anchor_quotes(
    full_text: str,
    promises: list[ExtractedPromise],
    fuzzy_threshold: float = 0.62,
):
    """Step 3: 将承诺和兑现证据定位到原文（同步）"""
    for i, promise in enumerate(promises):
        if promise.claim_text:
            result = locate_quote(full_text, promise.claim_text, fuzzy_threshold=fuzzy_threshold)
            yield LedgerBuildEvent("anchored", {
                "type": "claim",
                "claim_text": promise.claim_text,
                "anchor_status": result.status.value,
                "char_start": result.char_start,
                "char_end": result.char_end,
                "section": result.section,
                "confidence": result.confidence,
            })

        if promise.discharge_text:
            result = locate_quote(full_text, promise.discharge_text, fuzzy_threshold=fuzzy_threshold)
            yield LedgerBuildEvent("anchored", {
                "type": "discharge",
                "claim_text": promise.claim_text,
                "anchor_status": result.status.value,
                "char_start": result.char_start,
                "char_end": result.char_end,
                "section": result.section,
                "confidence": result.confidence,
            })

    return promises


async def run_ledger_build(
    full_text: str,
    literature_id: str = "",
    call_llm: Optional[callable] = None,
    fuzzy_threshold: float = 0.62,
):
    """运行完整的台账构建流水线（4 步，异步）

    严格参考 scholar-assistant-agent-main 中该功能的实现：
    - 使用 _extract_promise_zone 提取承诺区域
    - 使用 extract_json_object / extract_json_array（3 阶段 JSON 解析）
    - 2 次 LLM 重试机制
    - 逐个承诺兑现检查（每条款单独调用 LLM）

    Args:
        full_text: 论文全文
        literature_id: 论文 ID
        call_llm: 异步 LLM 调用函数（async fn(prompt, system) -> str）
        fuzzy_threshold: 模糊匹配阈值

    Yields:
        LedgerBuildEvent — SSE 事件流

    Returns:
        list[ExtractedPromise] — 构建完成的承诺列表
    """
    promises: list[ExtractedPromise] = []

    # Step 1: 异步提取承诺
    async for event in extract_promises(full_text, literature_id, call_llm):
        if event.event == "promise_extracted":
            promises.append(ExtractedPromise(
                claim_text=event.data.get("claim_text", ""),
                severity=event.data.get("severity", "info"),
                section_hint=event.data.get("section_hint", ""),
            ))
        yield event

    logger.info("run_ledger_build: extracted %d promises", len(promises))
    if not promises:
        logger.warning("run_ledger_build: no promises extracted, yielding complete event")
        yield LedgerBuildEvent("complete", {
            "total": 0,
            "message": "未识别出承诺",
        })
        return

    # Step 2: 逐个检查兑现（每条款单独调用 LLM）
    async for event in check_discharge(full_text, promises, call_llm):
        if event.event == "promise_checked":
            for p in promises:
                if p.claim_text == event.data.get("claim_text", ""):
                    p.status = event.data.get("status", "unpaid")
                    p.discharge_text = event.data.get("discharge_text", "")
                    break
        yield event

    # Step 3: 定位引文（同步）
    for event in anchor_quotes(full_text, promises, fuzzy_threshold):
        yield event

    total = len(promises)
    paid = sum(1 for p in promises if p.status == "paid")
    partial = sum(1 for p in promises if p.status == "partial")
    unpaid = sum(1 for p in promises if p.status == "unpaid")

    yield LedgerBuildEvent("complete", {
        "total": total,
        "paid": paid,
        "partial": partial,
        "unpaid": unpaid,
        "message": f"台账构建完成: 共 {total} 条承诺, {paid} 已兑现, {partial} 部分兑现, {unpaid} 未兑现",
    })

    return
