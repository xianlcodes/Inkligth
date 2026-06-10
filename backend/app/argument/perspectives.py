"""
多角度评审的个体视角实现（异步）

四个评审视角：
  - methodology:     研究方法论
  - experiment:      实验设计
  - writing:         写作质量
  - devils_advocate: 魔鬼代言人（对抗性质疑）
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.argument.json_extract import extract_json_array

logger = logging.getLogger(__name__)


@dataclass
class ReviewPointData:
    """单条评审意见"""
    category: str
    severity: str                    # major | minor | critical
    title: str
    description: str
    suggestion: str = ""
    anchor_ref: str = ""


# ── Prompt templates (每个视角独立) ──

SYSTEM_PROMPTS = {
    "methodology": """你是一位专注于**研究方法论**的严谨审稿人。
请从以下角度评审论文的方法论：
1. 研究问题是否明确定义
2. 方法论选择是否合理
3. 理论框架是否完善
4. 假设是否清晰且合理
5. 方法局限性是否被讨论
6. 与其他方法的对比是否公平

请输出 JSON 格式评审意见。""",

    "experiment": """你是一位专注于**实验设计**的严谨审稿人。
请从以下角度评审论文的实验：
1. 实验设计是否合理（对照组、变量控制等）
2. 数据集选择是否适当
3. 评估指标是否全面且有意义
4. 实验结果是否有统计学显著性
5. 实验是否可复现
6. 消融实验是否充分
7. 是否有潜在的实验偏差

请输出 JSON 格式评审意见。""",

    "writing": """你是一位专注于**学术写作质量**的审稿人。
请从以下角度评审论文的写作：
1. 结构是否清晰、逻辑是否连贯
2. 术语使用是否准确一致
3. 图表是否清晰有效
4. 引用是否适当且全面
5. 语言表达是否简洁准确
6. 摘要和结论是否准确反映内容

请输出 JSON 格式评审意见。""",

    "devils_advocate": """你是一位**魔鬼代言人**，需要从对抗性角度挑战论文的各个部分。
请提出尖锐但建设性的质疑：
1. 该方法的实际应用价值有多大？是否有过度承诺？
2. 是否有未充分考虑的替代解释？
3. 实验结果是否真的支持作者的结论？
4. 是否有隐藏的假设或局限性被忽略？
5. 与现有方法相比，改进是否显著？
6. 是否有潜在的伦理问题或社会影响？

请输出 JSON 格式评审意见。""",
}

REVIEW_PROMPT_TEMPLATE = """请评审以下论文内容，给出 {max_points} 条以内的评审意见。

论文内容：
{full_text}

请输出严格的 JSON 格式：
```json
[
  {{
    "severity": "major | minor | critical",
    "title": "简短的问题标题（20字以内）",
    "description": "详细的问题描述",
    "suggestion": "修改建议（可选）",
    "anchor_ref": "相关原文引用（可选）"
  }}
]
```

要求：
- severity: critical=致命问题, major=重要问题, minor=次要问题
- 每条意见必须针对论文中的具体问题
- description 应有理有据，避免空泛评价
- 如果论文内容过少或没有可评之处，返回空数组 []
"""


async def run_perspective_review(
    category: str,
    full_text: str,
    max_points: int = 5,
    call_llm: Optional[callable] = None,
) -> list[ReviewPointData]:
    """运行单个视角的评审（异步）

    Args:
        category: 视角名称 (methodology|experiment|writing|devils_advocate)
        full_text: 论文全文
        max_points: 最多输出条数
        call_llm: 异步 LLM 调用函数 (async fn(prompt, system) -> str)

    Returns:
        list[ReviewPointData]
    """
    system_prompt = SYSTEM_PROMPTS.get(category, "")

    truncated = full_text[:8000] if len(full_text) > 8000 else full_text

    user_prompt = REVIEW_PROMPT_TEMPLATE.format(
        full_text=truncated,
        max_points=max_points,
    )

    try:
        response = await call_llm(user_prompt, system=system_prompt)
        items = extract_json_array(response) or []

        points = []
        for item in items:
            points.append(ReviewPointData(
                category=category,
                severity=item.get("severity", "minor"),
                title=item.get("title", ""),
                description=item.get("description", ""),
                suggestion=item.get("suggestion", ""),
                anchor_ref=item.get("anchor_ref", ""),
            ))

        logger.info(
            "Perspective '%s' produced %d review points",
            category, len(points),
        )
        return points

    except Exception as e:
        logger.exception("Perspective '%s' failed: %s", category, e)
        return []


async def run_parallel_review(
    full_text: str,
    perspectives: list[str],
    max_points_per_perspective: int = 5,
    call_llm: Optional[callable] = None,
) -> dict[str, list[ReviewPointData]]:
    """并行运行多个视角的评审（异步）

    Args:
        full_text: 论文全文
        perspectives: 视角名称列表
        max_points_per_perspective: 每个视角最多条数
        call_llm: 异步 LLM 调用函数

    Returns:
        {category: [ReviewPointData, ...]}
    """
    valid = {"methodology", "experiment", "writing", "devils_advocate"}
    selected = [p for p in perspectives if p in valid]

    results: dict[str, list[ReviewPointData]] = {}
    for category in selected:
        results[category] = await run_perspective_review(
            category=category,
            full_text=full_text,
            max_points=max_points_per_perspective,
            call_llm=call_llm,
        )

    return results


# ═══════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════

