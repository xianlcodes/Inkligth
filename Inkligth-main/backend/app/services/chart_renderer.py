"""实验数据图表自动生成 — matplotlib/seaborn → PNG"""

import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

SUPPORTED_CHART_TYPES = {"bar", "line", "radar", "confusion_matrix",
                         "scatter", "ablation_table"}


class ChartRenderer:
    """根据 LLM 的 chart_data_hint 生成科研图表"""

    def __init__(self, cache_dir: str, theme_colors: Optional[dict] = None):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.colors = theme_colors or {
            "primary": "#1E3A5F",
            "secondary": "#4A90D9",
            "accent": "#00B4D8",
        }

    def render(self, chart_type: str, data_hint: str,
               theme_name: str = "cs") -> Optional[str]:
        """
        根据 chart_type 和数据描述生成图表 PNG。

        chart_type: "bar" | "line" | "radar" | "confusion_matrix" | "scatter"
        data_hint: LLM 提供的文字描述，如 "Ours=92.3, BaselineA=87.1, BaselineB=84.5"
        返回 PNG 文件路径，失败返回 None。
        """
        if chart_type not in SUPPORTED_CHART_TYPES:
            logger.warning(f"Unsupported chart type: {chart_type}")
            return None

        cache_key = hashlib.md5(
            f"{chart_type}|{data_hint}|{theme_name}".encode()
        ).hexdigest()[:16]
        cache_path = os.path.join(self.cache_dir,
                                  f"chart_{cache_key}.png")
        if os.path.exists(cache_path):
            return cache_path

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import seaborn as sns

            plt.rcParams.update({
                "font.family": "sans-serif",
                "axes.unicode_minus": False,
                "figure.dpi": 200,
            })

            # 从 data_hint 解析数据
            data = self._parse_data_hint(data_hint)

            fig, ax = plt.subplots(figsize=(8, 4.5))
            fig.patch.set_alpha(0)

            if chart_type == "bar":
                self._render_bar(ax, data)
            elif chart_type == "line":
                self._render_line(ax, data)
            elif chart_type == "radar":
                self._render_radar(ax, data)
            elif chart_type == "confusion_matrix":
                self._render_confusion(ax, data)
            elif chart_type == "scatter":
                self._render_scatter(ax, data)

            # 去除多余边框
            sns.despine(ax=ax)
            plt.tight_layout()
            plt.savefig(cache_path, dpi=200, bbox_inches="tight",
                        transparent=True)
            plt.close(fig)

            return cache_path

        except Exception as e:
            logger.warning(f"Chart rendering failed for {chart_type}: {e}")
            return None

    def _parse_data_hint(self, hint: str) -> dict:
        """从文字描述中解析 {label: value} 或 {label: [values]}"""
        import re
        pairs = re.findall(r'(\w[\w\s]*?)\s*=\s*([\d.]+)', hint)
        result = {}
        for label, value_str in pairs:
            key = label.strip()
            try:
                result[key] = float(value_str)
            except ValueError:
                continue
        return result

    def _render_bar(self, ax, data: dict):
        """柱状图，用于对比基线方法"""
        labels = list(data.keys())
        values = list(data.values())
        colors = [self.colors["primary"], self.colors["secondary"],
                  self.colors["accent"], "#D4A843", "#E25822"]
        bars = ax.bar(labels, values,
                      color=colors[:len(labels)],
                      edgecolor="white", linewidth=0.5)
        # 在柱子顶部标注数值
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(values) * 0.01,
                    f"{val:.1f}", ha="center", va="bottom",
                    fontsize=10)
        ax.set_ylim(0, max(values) * 1.15)

    def _render_line(self, ax, data: dict):
        """折线图，用于收敛曲线"""
        labels = list(data.keys())
        values = list(data.values())
        ax.plot(range(len(values)), values,
                color=self.colors["primary"],
                linewidth=2, marker="o", markersize=6)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)

    def _render_radar(self, ax, data: dict):
        """雷达图，用于多维度能力对比"""
        labels = list(data.keys())
        values = list(data.values())
        angles = [n / len(labels) * 2 * 3.14159 for n in range(len(labels))]
        values += values[:1]
        angles += angles[:1]
        ax.plot(angles, values, color=self.colors["primary"], linewidth=2)
        ax.fill(angles, values, alpha=0.1, color=self.colors["primary"])
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=9)

    def _render_confusion(self, ax, data: dict):
        """混淆矩阵热力图"""
        import numpy as np
        labels = list(data.keys())[:4] or ["A", "B", "C", "D"]
        size = len(labels)
        matrix = np.random.rand(size, size) * 100  # 占位数据
        sns.heatmap(matrix, annot=True, fmt=".1f",
                     xticklabels=labels, yticklabels=labels,
                     cmap="Blues", ax=ax, cbar=False)

    def _render_scatter(self, ax, data: dict):
        """散点图，用于相关性分析"""
        items = list(data.items())
        if len(items) < 4:
            return self._render_bar(ax, data)
        xs = list(range(len(items)))
        ys = [v for _, v in items]
        ax.scatter(xs, ys, color=self.colors["secondary"], s=60, alpha=0.8)
        ax.set_xticks(xs)
        ax.set_xticklabels([k for k, _ in items], rotation=30,
                           ha="right", fontsize=9)
