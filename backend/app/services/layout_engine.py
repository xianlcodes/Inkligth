"""智能布局引擎 — 根据 page_type 和内容自动选择布局模板"""

from dataclasses import dataclass, field
from typing import Optional

from app.services.ppt_theme import DisciplineTheme


# ── 布局描述结构 ──

@dataclass
class TextBlock:
    text: str
    font_size: float = 18           # pt
    font_weight: str = "normal"     # "normal" | "bold" | "light"
    color: str = "#1A1A2E"
    alignment: str = "left"         # "left" | "center" | "right"
    max_lines: int = 6
    x: float = 0.8                  # inches from left
    y: float = 2.0                  # inches from top
    width: float = 11.5
    height: float = 4.5


@dataclass
class ImageBlock:
    ref: str = ""
    image_path: str = ""
    x: float = 0.8
    y: float = 2.0
    width: float = 6.0
    height: float = 4.5
    fit_mode: str = "contain"       # "contain" | "cover" | "stretch"


@dataclass
class ChartBlock:
    chart_type: str = "bar"
    data_hint: str = ""
    x: float = 0.8
    y: float = 2.0
    width: float = 11.5
    height: float = 4.5


@dataclass
class FormulaBlock:
    latex: str = ""
    x: float = 0.8
    y: float = 2.0
    width: float = 11.5
    height: float = 2.0


@dataclass
class SlideLayout:
    """单页幻灯片布局决策结果"""
    page_type: str
    slide_number: int
    theme: str = "cs"
    background_style: str = "solid"  # "solid" | "gradient" | "accent_bar"
    accent_bar: bool = True

    title: str = ""
    title_font_size: float = 34
    title_color: str = "#1A1A2E"

    text_blocks: list = field(default_factory=list)
    image_blocks: list = field(default_factory=list)
    chart_blocks: list = field(default_factory=list)
    formula_blocks: list = field(default_factory=list)

    note: str = ""


@dataclass
class LayoutPlan:
    """完整 PPT 的布局计划"""
    slides: list = field(default_factory=list)
    theme_name: str = "cs"


# ── 布局常量 ──

# 安全边距（对应 ~1.5cm/2cm）
MARGIN_LR = 0.8    # inches (左右)
MARGIN_TB = 0.5    # inches (上下)

CONTENT_WIDTH = 13.333 - MARGIN_LR * 2   # ≈ 11.733
CONTENT_HEIGHT = 7.5 - MARGIN_TB * 2 - 1.5  # 预留标题区

TITLE_TOP = 0.6
TITLE_LEFT = MARGIN_LR
TITLE_WIDTH = CONTENT_WIDTH
TITLE_HEIGHT = 1.0

BODY_TOP = 2.0
BODY_LEFT = MARGIN_LR
BODY_WIDTH = CONTENT_WIDTH
BODY_HEIGHT = 4.8

COLUMN_GAP = 0.4
COLUMN_WIDTH = (BODY_WIDTH - COLUMN_GAP) / 2  # ≈ 5.67

# page_type → 布局模板选择
PAGE_TYPE_LAYOUTS = {
    "title":              "centered",
    "section_header":     "full_bg",
    "bullet_text":        "single_column",
    "dual_column":        "two_column",
    "figure_full":        "image_full",
    "figure_text":        "image_left_text_right",
    "comparison_table":   "table_full",
    "formula_derivation": "formula_top",
    "data_chart":         "chart_center",
    "timeline":           "single_column",
}


# ── 核心布局引擎 ──

class LayoutEngine:
    """根据增强大纲 + 学科主题，为每张幻灯片分配布局"""

    def decide(self, slide: dict, theme: DisciplineTheme,
               visual_assets: Optional[dict] = None,
               slide_number: int = 1) -> SlideLayout:
        """为单个幻灯片做布局决策"""
        page_type = slide.get("page_type", "bullet_text")
        layout = SlideLayout(
            page_type=page_type,
            slide_number=slide_number,
            theme=theme.name,
            accent_bar=theme.accent_bar,
            title=slide.get("title", ""),
            title_font_size=theme.font_sizes["title"],
            title_color=theme.text_primary,
            note=slide.get("notes", "") or "",
        )

        # 根�据 page_type 填充相应的 blocks
        if page_type == "title":
            self._layout_title(layout, theme)
        elif page_type == "section_header":
            self._layout_section_header(layout, theme)
        elif page_type == "bullet_text":
            self._layout_bullet_text(layout, slide, theme)
        elif page_type == "dual_column":
            self._layout_dual_column(layout, slide, theme)
        elif page_type == "figure_full":
            self._layout_figure_full(layout, slide, visual_assets)
        elif page_type == "figure_text":
            self._layout_figure_text(layout, slide, visual_assets, theme)
        elif page_type == "comparison_table":
            self._layout_comparison_table(layout, slide, theme)
        elif page_type == "formula_derivation":
            self._layout_formula(layout, slide, theme)
        elif page_type == "data_chart":
            self._layout_data_chart(layout, slide, theme)
        else:
            self._layout_bullet_text(layout, slide, theme)

        return layout

    def _layout_title(self, layout: SlideLayout, theme: DisciplineTheme):
        """封面页 — 居中大字"""
        layout.title_font_size = 40
        layout.title_color = theme.primary_color
        layout.accent_bar = False

    def _layout_section_header(self, layout: SlideLayout, theme: DisciplineTheme):
        """章节过渡 — 全屏色块"""
        layout.background_style = "gradient"
        layout.title_font_size = 38
        layout.title_color = theme.text_light
        layout.accent_bar = False

    def _layout_bullet_text(self, layout: SlideLayout, slide: dict,
                            theme: DisciplineTheme):
        """纯文字要点页"""
        bullets = slide.get("bullets", [])
        text = "\n".join(f"• {b}" for b in bullets) if bullets else ""
        layout.text_blocks.append(TextBlock(
            text=text,
            font_size=theme.font_sizes["body"],
            color=theme.text_primary,
            x=BODY_LEFT, y=BODY_TOP,
            width=BODY_WIDTH, height=BODY_HEIGHT,
        ))

    def _layout_dual_column(self, layout: SlideLayout, slide: dict,
                            theme: DisciplineTheme):
        """双栏布局"""
        bullets = slide.get("bullets", [])
        mid = len(bullets) // 2
        left_bullets = bullets[:mid] if mid > 0 else bullets[:2]
        right_bullets = bullets[mid:] if mid > 0 else bullets[2:]

        left_text = "\n".join(f"• {b}" for b in left_bullets)
        right_text = "\n".join(f"• {b}" for b in right_bullets)

        layout.text_blocks.append(TextBlock(
            text=left_text, font_size=theme.font_sizes["body"],
            color=theme.text_primary,
            x=BODY_LEFT, y=BODY_TOP,
            width=COLUMN_WIDTH, height=BODY_HEIGHT,
        ))
        if right_text:
            layout.text_blocks.append(TextBlock(
                text=right_text, font_size=theme.font_sizes["body"],
                color=theme.text_secondary,
                x=BODY_LEFT + COLUMN_WIDTH + COLUMN_GAP, y=BODY_TOP,
                width=COLUMN_WIDTH, height=BODY_HEIGHT,
            ))

    def _layout_figure_full(self, layout: SlideLayout, slide: dict,
                            visual_assets: Optional[dict]):
        """全页图"""
        ref = slide.get("visual_ref")
        if ref and visual_assets:
            for fig in visual_assets.get("figures", []):
                if fig["id"] == ref and fig.get("image_path"):
                    layout.image_blocks.append(ImageBlock(
                        ref=ref, image_path=fig["image_path"],
                        x=MARGIN_LR, y=0.8,
                        width=CONTENT_WIDTH, height=5.5,
                        fit_mode="contain",
                    ))

    def _layout_figure_text(self, layout: SlideLayout, slide: dict,
                            visual_assets: Optional[dict],
                            theme: DisciplineTheme):
        """左图右文"""
        ref = slide.get("visual_ref")
        image_w = BODY_WIDTH * 0.55
        text_w = BODY_WIDTH * 0.4

        if ref and visual_assets:
            for fig in visual_assets.get("figures", []):
                if fig["id"] == ref and fig.get("image_path"):
                    layout.image_blocks.append(ImageBlock(
                        ref=ref, image_path=fig["image_path"],
                        x=BODY_LEFT, y=BODY_TOP,
                        width=image_w, height=BODY_HEIGHT,
                        fit_mode="contain",
                    ))

        bullets = slide.get("bullets", [])
        text = "\n".join(f"• {b}" for b in bullets) if bullets else ""
        layout.text_blocks.append(TextBlock(
            text=text, font_size=theme.font_sizes["body"],
            color=theme.text_primary,
            x=BODY_LEFT + image_w + COLUMN_GAP, y=BODY_TOP,
            width=text_w, height=BODY_HEIGHT,
        ))

    def _layout_comparison_table(self, layout: SlideLayout, slide: dict,
                                 theme: DisciplineTheme):
        """对比表格页 — 以文字列表方式呈现"""
        bullets = slide.get("bullets", [])
        text = "\n".join(f"• {b}" for b in bullets) if bullets else ""
        layout.text_blocks.append(TextBlock(
            text=text,
            font_size=theme.font_sizes["body"] - 2,
            color=theme.text_primary,
            x=BODY_LEFT, y=BODY_TOP,
            width=BODY_WIDTH, height=BODY_HEIGHT,
        ))

    def _layout_formula(self, layout: SlideLayout, slide: dict,
                        theme: DisciplineTheme):
        """公式页 — 公式在上，解释在下"""
        ref = slide.get("visual_ref")
        # 如果有公式资产，留出公式区域
        formula_h = 2.5
        layout.formula_blocks.append(FormulaBlock(
            latex=ref or "",
            x=BODY_LEFT, y=BODY_TOP,
            width=BODY_WIDTH, height=formula_h,
        ))

        bullets = slide.get("bullets", [])
        text = "\n".join(f"• {b}" for b in bullets) if bullets else ""
        layout.text_blocks.append(TextBlock(
            text=text, font_size=theme.font_sizes["body"],
            color=theme.text_primary,
            x=BODY_LEFT, y=BODY_TOP + formula_h + 0.3,
            width=BODY_WIDTH, height=BODY_HEIGHT - formula_h,
        ))

    def _layout_data_chart(self, layout: SlideLayout, slide: dict,
                           theme: DisciplineTheme):
        """图表页 — 图表居中，下方标注"""
        chart_type = slide.get("suggested_chart", "bar")
        data_hint = slide.get("chart_data_hint", "")
        chart_h = 3.5

        layout.chart_blocks.append(ChartBlock(
            chart_type=chart_type,
            data_hint=data_hint,
            x=BODY_LEFT, y=BODY_TOP,
            width=BODY_WIDTH, height=chart_h,
        ))

        bullets = slide.get("bullets", [])
        text = "\n".join(f"• {b}" for b in bullets) if bullets else ""
        layout.text_blocks.append(TextBlock(
            text=text, font_size=theme.font_sizes["caption"] + 2,
            color=theme.text_secondary,
            x=BODY_LEFT, y=BODY_TOP + chart_h + 0.2,
            width=BODY_WIDTH, height=BODY_HEIGHT - chart_h,
        ))


# ── 溢出处理 ──

def estimate_text_lines(text: str, font_size: float,
                        max_width_inches: float) -> int:
    """估算文本所需行数（近似）"""
    # 平均中文字符宽度 ≈ font_size * 0.045 inches
    chars_per_line = max(1, int(max_width_inches / (font_size * 0.045)))
    total_chars = len(text)
    # 按换行符分割
    lines = text.split("\n")
    total_lines = sum(max(1, -(-len(ln) // chars_per_line)) for ln in lines)
    return total_lines


def handle_text_overflow(text_block: TextBlock,
                         max_lines: int = 6) -> bool:
    """
    检查文本是否溢出，如果是则自动缩减。
    返回 True 表示缩减成功，False 表示需要分页。
    """
    estimated = estimate_text_lines(
        text_block.text, text_block.font_size, text_block.width
    )
    if estimated <= max_lines:
        return True

    # Level 1: 缩小字号（步长 1pt，最小至 14pt）
    while estimated > max_lines and text_block.font_size > 14:
        text_block.font_size -= 1
        estimated = estimate_text_lines(
            text_block.text, text_block.font_size, text_block.width
        )

    if estimated <= max_lines:
        return True

    # Level 2: 减少可见行数（截断）
    lines = text_block.text.split("\n")
    text_block.text = "\n".join(lines[:max_lines])
    return len(lines) <= max_lines  # False if still need pagination
