import json
import logging
import re
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

NARRATIVE_OUTLINE_PROMPT = """You are an academic presentation designer. Based on the following paper, generate a presentation outline in JSON format for a group meeting report.

Use this narrative structure (NOT the paper's original section order):
1. Title Slide — paper title, authors, journal/year
2. Background & Pain Points — current state, key limitations of existing work
3. Core Innovation (3 points) — what the paper does differently, its "selling points"
4. Method Overview — system pipeline / architecture overview
5. Method Details — core technical details (formula / algorithm / network block)
6. Experimental Setup — datasets, metrics, baselines, implementation details
7. Main Results — key experimental results, cite figure/table numbers
8. Ablation Studies — ablation experiments, parameter sensitivity, visual analysis
9. Case Study / Qualitative Analysis — concrete examples
10. Conclusion & Outlook — contributions, limitations, future work

IMPORTANT CONTENT REQUIREMENTS:
- Each bullet MUST contain SPECIFIC numbers, metrics, or concrete details from the paper
- Good: "在 ImageNet 上 Top-1 准确率达到 88.5%，比 ResNet-152 高出 3.2%"
- Bad: "模型在多个数据集上取得了最优结果"
- When describing methods, explain WHAT was done and WHY it works
- When describing results, ALWAYS cite specific figure/table numbers from the paper (e.g., "如 Fig. 3 所示", "见表 2")
- Total 8-12 slides, each with 3-5 bullets

Return ONLY valid JSON with this exact structure:
{
  "slides": [
    {
      "title": "Assertive slide title in Chinese (e.g. 'Transformer 彻底改变了序列建模')",
      "bullets": ["Specific bullet with numbers and details", "Bullet 2", "..."],
      "notes": "Speaker notes with transition cues",
      "page_type": "bullet_text",
      "visual_ref": null,
      "suggested_chart": null,
      "chart_data_hint": null
    }
  ]
}

Page types:
- title: Centered title slide
- section_header: Full-screen section divider
- bullet_text: Single-column text with bullet points
- dual_column: Left-right comparison layout
- figure_full: Full-page figure (use when citing an important figure)
- figure_text: Left-image right-text 60/40 (use when referencing a figure)
- comparison_table: Full-page comparison table
- formula_derivation: Formula at top, explanation below
- data_chart: Auto-generated data visualization (bar/line)
- timeline: Horizontal timeline / architecture flow

Title style: assertive claim, NOT descriptive label. Use Chinese.
visual_ref: For slides that critically depend on a figure/table, set this to the figure/table reference as it appears in the paper (e.g. "Fig. 3", "Table 2", "Figure 1"). Set to null if not applicable.
All content in Chinese (technical terms may keep English origin with Chinese parenthetical).

Return ONLY valid JSON, no markdown code blocks, no extra text.

Paper content:
{text}"""


class OutlineGenerator:
    def __init__(self, client: AsyncOpenAI, model: str):
        self.client = client
        self.model = model

    async def generate(self, text: str, title: str = "", authors: str = "", year: str = "", journal: str = "",
                       visual_summary: str = "") -> dict:
        context_parts = []
        if title:
            context_parts.append(f"Title: {title}")
        if authors:
            context_parts.append(f"Authors: {authors}")
        if year:
            context_parts.append(f"Year: {year}")
        if journal:
            context_parts.append(f"Journal: {journal}")
        if visual_summary:
            context_parts.append(f"\nVisual assets available in PDF:\n{visual_summary}")

        # 增加输入长度，让 LLM 看到更多论文内容
        paper_text = text[:25000]
        context_parts.append(f"\nContent:\n{paper_text}")
        context = "\n".join(context_parts)

        prompt = NARRATIVE_OUTLINE_PROMPT.replace("{text}", context)

        logger.info(f"Calling AI outline generation with model: {self.model}")
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            timeout=180.0,
        )

        content = response.choices[0].message.content.strip()
        logger.info(f"AI outline response received, length: {len(content)}")

        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse outline JSON, raw: {content[:500]}")
            result = {"slides": []}

        if "slides" not in result:
            result["slides"] = []

        # 确保每页字段完整且类型正确
        for slide in result["slides"]:
            slide.setdefault("page_type", "bullet_text")
            slide.setdefault("visual_ref", None)
            slide.setdefault("suggested_chart", None)
            slide.setdefault("chart_data_hint", None)
            # 强制字符串类型
            for field in ("chart_data_hint", "visual_ref", "suggested_chart"):
                val = slide.get(field)
                if val is not None and not isinstance(val, str):
                    slide[field] = str(val)

        return result


def auto_match_visual_refs(slides: list[dict],
                           visual_assets: dict | None) -> list[dict]:
    """
    后处理步骤：扫描每张 slide 的标题和要点，查找对图/表的引用，
    自动匹配到 visual_assets 中提取的实际资产。

    匹配策略（按优先级）：
    1. 如果 LLM 已设置 visual_ref 且能匹配到资产 → 直接保留
    2. 搜索 "Fig. N" / "Figure N" / "表 N" / "Table N" / "如图 N" → 按 caption 匹配
    3. 对于结果/实验相关幻灯片，没有文字引用时尝试按位置分配 figure
    """
    if not visual_assets:
        return slides

    all_assets = []
    all_assets.extend(visual_assets.get("figures", []))
    all_assets.extend(visual_assets.get("tables", []))

    if not all_assets:
        return slides

    # 建立索引
    page_assets: dict[int, list[dict]] = {}
    id_to_asset: dict[str, dict] = {}
    for a in all_assets:
        page_assets.setdefault(a["page_number"], []).append(a)
        id_to_asset[a["id"]] = a

    fig_pattern = re.compile(
        r'(?:Fig(?:ure)?\.?\s*|表\s*|Table\s*|如图\s*)(\d+)',
        re.IGNORECASE,
    )

    for slide in slides:
        # 优先级 1: 已有有效 visual_ref → 跳过
        existing_ref = slide.get("visual_ref")
        if existing_ref and existing_ref in id_to_asset:
            continue

        haystack = " ".join([
            slide.get("title", ""),
            *slide.get("bullets", []),
        ])

        matches = fig_pattern.findall(haystack)

        if matches:
            fig_num = int(matches[0])
            best = _find_by_caption_or_page(all_assets, page_assets, fig_num)
            if best:
                slide["visual_ref"] = best["id"]
                _upgrade_page_type_for_image(slide, best)
                continue

        # 优先级 3: 结果页（slide 6-9）尝试分配 figure
        slide_idx = slides.index(slide)  # 0-indexed
        if 5 <= slide_idx <= 8 and not slide.get("visual_ref"):
            # 找还没被引用的 figure
            used_ids = {s.get("visual_ref") for s in slides if s.get("visual_ref")}
            for a in all_assets:
                if a["id"] not in used_ids and a.get("image_path"):
                    slide["visual_ref"] = a["id"]
                    _upgrade_page_type_for_image(slide, a)
                    break

    return slides


def _find_by_caption_or_page(all_assets: list[dict],
                              page_assets: dict[int, list[dict]],
                              fig_num: int) -> dict | None:
    """按 caption 文本中的数字匹配，fallback 到页码匹配"""
    # 先精确匹配 caption
    for a in all_assets:
        caption = (a.get("caption") or "").lower()
        if re.search(rf'\bfig\.?\s*{fig_num}\b', caption, re.IGNORECASE) or \
           re.search(rf'\btable\s*{fig_num}\b', caption, re.IGNORECASE) or \
           re.search(rf'\b{figure_num_words(fig_num)}\b', caption):
            return a
    # 按数字字符串匹配
    for a in all_assets:
        if str(fig_num) in (a.get("caption") or ""):
            return a
    # fallback: 页码附近
    for pn in range(max(1, fig_num - 1), fig_num + 2):
        if pn in page_assets:
            return page_assets[pn][0]
    return None


def figure_num_words(n: int) -> str:
    """1 → '一', 2 → '二', 等（用于匹配中文数字）"""
    mapping = "零一二三四五六七八九"
    return "".join(mapping[int(d)] for d in str(n) if d.isdigit())


def _upgrade_page_type_for_image(slide: dict, asset: dict):
    """当 slide 匹配到图片资产时，自动升级 page_type"""
    if not asset.get("image_path"):
        return
    current_type = slide.get("page_type", "bullet_text")
    if current_type in ("bullet_text", "dual_column"):
        has_long_bullets = any(len(b or "") > 30 for b in slide.get("bullets", []))
        slide["page_type"] = "figure_text" if has_long_bullets else "figure_full"
