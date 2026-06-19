"""学科主题注册表 — 定义四套专业配色/字体/布局参数"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DisciplineTheme:
    """学科主题定义"""
    name: str
    label: str

    # ── 配色系统 ──
    primary_color: str          # 主色（标题、装饰条）
    secondary_color: str        # 辅色（小标题、图标）
    accent_color: str           # 强调色（数据高亮、CTA 按钮）
    background_start: str       # 背景渐变起始色
    background_end: str         # 背景渐变终止色
    card_bg: str                # 内容卡片背景
    text_primary: str           # 正文主色
    text_secondary: str         # 次要文字色
    text_light: str             # 浅色文字（深色底）
    divider_color: str          # 分割线

    # ── 字体配置 ──
    font_title: str = "Arial"           # 标题字体
    font_body: str = "Calibri"          # 正文字体
    font_sizes: dict = field(default_factory=lambda: {
        "title": 34, "subtitle": 22, "body": 18, "caption": 12,
    })

    # ── 布局偏好 ──
    accent_bar: bool = True     # 顶部装饰条
    corner_radius_inches: float = 0.06
    shadow_enabled: bool = True


# ── 四大学科主题 ──

CS_THEME = DisciplineTheme(
    name="cs", label="计算机科学",
    primary_color="#1E3A5F", secondary_color="#4A90D9",
    accent_color="#00B4D8",
    background_start="#F5F8FC", background_end="#FFFFFF",
    card_bg="#FFFFFF",
    text_primary="#1A1A2E", text_secondary="#4A4A6A",
    text_light="#F0F4F8", divider_color="#D0DCE8",
    font_sizes={"title": 34, "subtitle": 22, "body": 18, "caption": 12},
    accent_bar=True, shadow_enabled=True,
)

MEDICAL_THEME = DisciplineTheme(
    name="medical", label="生物医学",
    primary_color="#1B4D3E", secondary_color="#2D8A6E",
    accent_color="#D4A843",
    background_start="#F0F7F4", background_end="#FFFFFF",
    card_bg="#FFFFFF",
    text_primary="#1A2E1A", text_secondary="#4A6A4A",
    text_light="#F0F7F4", divider_color="#C0D6C8",
    font_sizes={"title": 34, "subtitle": 22, "body": 18, "caption": 12},
    accent_bar=True, shadow_enabled=True,
)

MATH_THEME = DisciplineTheme(
    name="math_physics", label="数理科学",
    primary_color="#1A1A2E", secondary_color="#3D5A80",
    accent_color="#E25822",
    background_start="#F8F9FA", background_end="#FFFFFF",
    card_bg="#FFFFFF",
    text_primary="#1A1A2E", text_secondary="#4A4A6A",
    text_light="#F8F9FA", divider_color="#D0D0E0",
    font_sizes={"title": 34, "subtitle": 22, "body": 18, "caption": 11},
    accent_bar=True, shadow_enabled=False,
)

HUMANITIES_THEME = DisciplineTheme(
    name="humanities", label="人文社科",
    primary_color="#4A3728", secondary_color="#8B6B4A",
    accent_color="#C0392B",
    background_start="#FDF8F4", background_end="#FFFFFF",
    card_bg="#FFFFFF",
    text_primary="#2C1810", text_secondary="#5C4033",
    text_light="#FDF8F4", divider_color="#DCC8B8",
    font_sizes={"title": 34, "subtitle": 22, "body": 18, "caption": 12},
    accent_bar=False, shadow_enabled=False,
)

THEME_REGISTRY: dict[str, DisciplineTheme] = {
    "cs": CS_THEME,
    "medical": MEDICAL_THEME,
    "math_physics": MATH_THEME,
    "humanities": HUMANITIES_THEME,
}

THEME_CHOICES = [
    {"value": k, "label": v.label}
    for k, v in THEME_REGISTRY.items()
]


def get_theme(name: str) -> DisciplineTheme:
    """获取主题，未知主题回退到 CS"""
    return THEME_REGISTRY.get(name, CS_THEME)
