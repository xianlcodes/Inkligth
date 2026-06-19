"""LaTeX 公式 → 高清 PNG 渲染器"""

import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class FormulaRenderer:
    """将 LaTeX 公式渲染为透明背景 PNG，供 PPT 嵌入"""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def render(self, latex: str, font_size: int = 36,
               dpi: int = 200) -> Optional[str]:
        """
        渲染公式为 PNG。

        策略：
        1. 计算 md5 缓存键，命中直接返回
        2. 尝试 matplotlib mathtext（快速、支持基础 LaTeX）
        3. 失败时返回 None，由调用方回退到论文原图
        """
        cache_key = hashlib.md5(
            f"{latex}|{font_size}|{dpi}".encode()
        ).hexdigest()[:16]
        cache_path = os.path.join(self.cache_dir, f"formula_{cache_key}.png")

        if os.path.exists(cache_path):
            return cache_path

        try:
            self._render_matplotlib(latex, font_size, dpi, cache_path)
            return cache_path
        except Exception as e:
            logger.warning(f"Formula rendering failed: {e}")
            return None

    def _render_matplotlib(self, latex: str, font_size: int,
                           dpi: int, output_path: str):
        """使用 matplotlib 的 mathtext 引擎渲染"""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # 清理 LaTeX：移除 \begin{align} / \end{align} 等复杂环境
        clean = self._simplify_latex(latex)

        fig, ax = plt.subplots(figsize=(8, 1.5))
        ax.axis("off")

        # 尝试用 $$ 包裹
        if not clean.startswith("$"):
            clean = f"${clean}$"

        ax.text(0.5, 0.5, clean, fontsize=font_size,
                ha="center", va="center",
                transform=ax.transAxes)

        plt.savefig(output_path, dpi=dpi, bbox_inches="tight",
                    pad_inches=0.1, transparent=True)
        plt.close(fig)

    def _simplify_latex(self, latex: str) -> str:
        """简化 LaTeX 使其能被 mathtext 解析"""
        replacements = [
            ("\\begin{align}", ""), ("\\end{align}", ""),
            ("\\begin{aligned}", ""), ("\\end{aligned}", ""),
            ("\\begin{equation}", ""), ("\\end{equation}", ""),
            ("\\begin{cases}", ""), ("\\end{cases}", ""),
            ("\\label{", "\\text{"),  # 移除 label
            ("\\tag{", "\\text{"),
            ("\\qquad", "  "), ("\\quad", " "),
            ("\\centering", ""),
            ("\\text", "\\mathrm"),
        ]
        result = latex
        for old, new in replacements:
            result = result.replace(old, new)
        return result.strip()
