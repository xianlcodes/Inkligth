"""
评审引擎 (Reviewer) — 异步

协调多角度评审流程：
  1. 并行运行各视角评审
  2. 合成评审结果（共识优势 + 首要问题）
  3. SSE 流式推送

每个步骤均以 async generator 形式输出事件，供 router 层 SSE 转发。
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.argument.json_extract import extract_json_object
from app.argument.perspectives import (
    ReviewPointData,
    run_parallel_review,
)

logger = logging.getLogger(__name__)


@dataclass
class ReviewEvent:
    """评审过程的 SSE 事件"""
    event: str                       # progress | review_point | synthesizing | assessment | complete | error
    data: dict = field(default_factory=dict)


@dataclass
class ReviewResult:
    """完整的评审结果"""
    points: list[ReviewPointData] = field(default_factory=list)
    overall_assessment: str = ""
    strengths: str = ""
    top_issues: str = ""


# ── Synthesis prompt ──

SYNTHESIS_PROMPT = """你是一位经验丰富的学术论文评审主席（Area Chair）。
以下是多位审稿人对同一篇论文的评审意见：

{all_reviews}

请综合所有意见，输出以下 JSON：
```json
{{
  "overall_assessment": "accept | minor | major | reject",
  "strengths": "论文的主要优势（2-3 点，200 字以内）",
  "top_issues": "最重要的改进建议列表（3-5 条，300 字以内，用 - 开头分行）"
}}
```

请遵循：
- overall_assessment: 综合考虑所有视角，给出整体评价
- strengths: 从多个视角中提炼共识优势
- top_issues: 跨视角的优先问题，按重要性排序
- 保持客观、专业
"""


async def run_review(
    full_text: str,
    perspectives: list[str],
    max_points_per_perspective: int = 5,
    call_llm: Optional[callable] = None,
):
    """运行完整的多角度评审流程（异步）

    Args:
        full_text: 论文全文
        perspectives: 视角列表
        max_points_per_perspective: 每个视角最多条数
        call_llm: 异步 LLM 调用函数 (async fn(prompt, system) -> str)

    Yields:
        ReviewEvent — SSE 事件流

    Returns:
        ReviewResult — 完整评审结果
    """
    all_points: list[ReviewPointData] = []

    # Step 1: 异步评审各视角
    yield ReviewEvent("progress", {
        "step": "reviewing",
        "message": f"正在从 {len(perspectives)} 个角度评审论文...",
        "perspectives": perspectives,
    })

    try:
        perspective_results = await run_parallel_review(
            full_text=full_text,
            perspectives=perspectives,
            max_points_per_perspective=max_points_per_perspective,
            call_llm=call_llm,
        )
    except Exception as e:
        logger.exception("Parallel review failed")
        yield ReviewEvent("error", {"step": "reviewing", "message": str(e)})
        return

    # 逐个视角输出结果
    for category, points in perspective_results.items():
        yield ReviewEvent("progress", {
            "step": "reviewing",
            "message": f"{category} 视角评审完成，共 {len(points)} 条意见",
            "category": category,
            "count": len(points),
        })

        for point in points:
            all_points.append(point)
            yield ReviewEvent("review_point", {
                "category": point.category,
                "severity": point.severity,
                "title": point.title,
                "description": point.description,
                "suggestion": point.suggestion,
                "anchor_ref": point.anchor_ref,
            })

    if not all_points:
        yield ReviewEvent("progress", {
            "step": "reviewing",
            "message": "所有视角均未产生评审意见",
        })
        return

    # Step 2: 异步合成评审结果
    yield ReviewEvent("synthesizing", {
        "message": "正在综合评审意见，生成总结...",
        "total_points": len(all_points),
    })

    try:
        synthesis_text = _format_reviews_for_synthesis(all_points)
        prompt = SYNTHESIS_PROMPT.format(all_reviews=synthesis_text)
        response = await call_llm(prompt, system="你是一个经验丰富的论文评审主席。")
        synthesis = extract_json_object(response) or {}

        result = ReviewResult(
            points=all_points,
            overall_assessment=synthesis.get("overall_assessment", "major"),
            strengths=synthesis.get("strengths", ""),
            top_issues=synthesis.get("top_issues", ""),
        )

        yield ReviewEvent("assessment", {
            "overall_assessment": result.overall_assessment,
            "strengths": result.strengths,
            "top_issues": result.top_issues,
        })

    except Exception as e:
        logger.exception("Synthesis failed")
        yield ReviewEvent("error", {"step": "synthesis", "message": str(e)})
        result = ReviewResult(points=all_points)

    yield ReviewEvent("complete", {
        "total_points": len(result.points),
        "overall_assessment": result.overall_assessment,
    })

    return


# ═══════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════

def _format_reviews_for_synthesis(points: list[ReviewPointData]) -> str:
    """将评审意见格式化为合成输入的文本"""
    lines = []
    for i, p in enumerate(points, 1):
        lines.append(f"[{p.category}] ({p.severity}) {p.title}")
        lines.append(f"  描述: {p.description}")
        if p.suggestion:
            lines.append(f"  建议: {p.suggestion}")
        lines.append("")
    return "\n".join(lines)


