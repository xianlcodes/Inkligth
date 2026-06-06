"""从 PDF 中提取视觉资产（图/表/公式），复用 DocLayout-YOLO 模型

支持基于 PDF 修改时间的缓存，避免重复提取。
"""

import hashlib
import json
import logging
import os
from typing import Optional

import fitz
import numpy as np

from app.utils.layout_model import get_layout_model

logger = logging.getLogger(__name__)

# 需要提取的布局类别
EXTRACT_CLASSES = {
    "figure": "figure",
    "table": "table",
    "isolate_formula": "formula",
    "formula_caption": "formula",
}

# 过滤掉的小图标面积阈值（占页面比例）
MIN_FIGURE_AREA_RATIO = 0.01

# 缓存版本号 — 提取逻辑有重大变化时递增以废弃旧缓存
CACHE_VERSION = 1


def _pdf_cache_key(pdf_path: str) -> str | None:
    """基于 PDF 路径 + 修改时间 + 文件大小的稳定缓存键"""
    try:
        stat = os.stat(pdf_path)
        raw = f"{os.path.abspath(pdf_path)}::{stat.st_mtime}::{stat.st_size}::v{CACHE_VERSION}"
        return hashlib.md5(raw.encode()).hexdigest()
    except OSError:
        return None


class VisualAsset:
    """PDF 中提取的单个视觉元素"""
    def __init__(self, asset_id: str, asset_type: str, page_number: int,
                 bbox: tuple, image: Optional[bytes] = None,
                 caption: str = "", alt_text: str = "",
                 latex_raw: str = ""):
        self.id = asset_id
        self.asset_type = asset_type  # "figure" | "table" | "formula"
        self.page_number = page_number
        self.bbox = bbox              # (x0, y0, x1, y1) 原始坐标
        self.image = image            # PNG bytes
        self.caption = caption
        self.alt_text = alt_text
        self.latex_raw = latex_raw
        self.image_path: Optional[str] = None  # 缓存路径

    def area_ratio(self, page_width: float, page_height: float) -> float:
        """计算元素占页面的面积比"""
        w = self.bbox[2] - self.bbox[0]
        h = self.bbox[3] - self.bbox[1]
        return (w * h) / (page_width * page_height)


class VisualExtractor:
    """从 PDF 提取视觉资产的主服务"""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    async def extract(self, pdf_path: str) -> dict:
        """
        全流程提取（带缓存）：
        1. 检查缓存 → 如果有效直接返回
        2. 逐页渲染 → DocLayout-YOLO 检测
        3. 分类提取 figure/table/formula
        4. 裁剪保存 PNG, 提取 LaTeX
        5. 写入缓存
        返回 {figures, tables, formulas, summary}
        """
        # ── 尝试从缓存加载 ──
        cached = self._load_cached(pdf_path)
        if cached is not None:
            logger.info("VisualExtractor cache HIT for %s", pdf_path)
            return cached

        logger.info("VisualExtractor cache MISS for %s, extracting...", pdf_path)

        model = await get_layout_model()
        doc = fitz.open(pdf_path)
        assets: list[VisualAsset] = []

        try:
            for pageno in range(doc.page_count):
                page = doc[pageno]
                pix = page.get_pixmap(dpi=200)
                img = np.frombuffer(pix.samples, np.uint8).reshape(
                    pix.height, pix.width, 3
                )[:, :, ::-1]

                page_layout = model.predict(
                    img, imgsz=int(pix.height / 32) * 32
                )[0]

                page_w = page.rect.width
                page_h = page.rect.height

                for d in page_layout.boxes:
                    cls_name = page_layout.names[int(d.cls)]
                    target_type = EXTRACT_CLASSES.get(cls_name)
                    if target_type is None:
                        continue

                    x0, y0, x1, y1 = d.xyxy
                    # 坐标缩放：从像素坐标转为 PDF 点坐标
                    scale_x = page_w / pix.width
                    scale_y = page_h / pix.height

                    asset = VisualAsset(
                        asset_id=f"{target_type}_{pageno + 1}_{int(x0)}_{int(y0)}",
                        asset_type=target_type,
                        page_number=pageno + 1,
                        bbox=(x0 * scale_x, y0 * scale_y,
                              x1 * scale_x, y1 * scale_y),
                    )

                    # 过滤小图标
                    if asset.area_ratio(page_w, page_h) < MIN_FIGURE_AREA_RATIO:
                        continue

                    if target_type in ("figure", "table"):
                        # 裁剪图像
                        clip_rect = fitz.Rect(
                            asset.bbox[0], asset.bbox[1],
                            asset.bbox[2], asset.bbox[3],
                        )
                        try:
                            clip_pix = page.get_pixmap(dpi=200, clip=clip_rect)
                            asset.image = clip_pix.tobytes("png")
                        except Exception:
                            pass

                        # 提取图注/表注（向上/下搜索文本）
                        asset.caption = self._extract_nearby_text(
                            page, asset.bbox
                        )

                    elif target_type == "formula":
                        # 提取该区域的文本作为 LaTeX 候选
                        formula_rect = fitz.Rect(
                            asset.bbox[0], asset.bbox[1],
                            asset.bbox[2], asset.bbox[3],
                        )
                        raw = page.get_text("text", clip=formula_rect).strip()
                        asset.latex_raw = self._clean_latex(raw)

                    assets.append(asset)

        finally:
            doc.close()

        # 保存图像并分类
        figures = []
        tables = []
        formulas = []
        for asset in assets:
            # 持久化图像
            if asset.image:
                md5 = hashlib.md5(asset.image).hexdigest()[:12]
                ext_path = os.path.join(self.cache_dir, f"{asset.id}_{md5}.png")
                with open(ext_path, "wb") as f:
                    f.write(asset.image)
                asset.image_path = ext_path

            item = {
                "id": asset.id,
                "asset_type": asset.asset_type,
                "page_number": asset.page_number,
                "caption": asset.caption,
                "image_path": asset.image_path,
                "latex_raw": asset.latex_raw,
                "alt_text": asset.alt_text,
            }

            if asset.asset_type == "figure":
                figures.append(item)
            elif asset.asset_type == "table":
                tables.append(item)
            elif asset.asset_type == "formula":
                formulas.append(item)

        summary = self._build_summary(figures, tables, formulas)

        result = {
            "figures": figures,
            "tables": tables,
            "formulas": formulas,
            "summary": summary,
        }

        # ── 写入缓存 ──
        self._save_cache(pdf_path, result)

        return result

    # ── 缓存相关方法 ──

    def _cache_path(self, pdf_path: str) -> str | None:
        key = _pdf_cache_key(pdf_path)
        if key is None:
            return None
        return os.path.join(self.cache_dir, f"manifest_{key}.json")

    def _load_cached(self, pdf_path: str) -> dict | None:
        """检查缓存，如果有效返回缓存结果。PNG 必须仍存在于磁盘上。"""
        cache_path = self._cache_path(pdf_path)
        if cache_path is None or not os.path.exists(cache_path):
            return None
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            # 验证所有 PNG 文件仍存在
            for group in ("figures", "tables", "formulas"):
                for item in manifest.get(group, []):
                    ip = item.get("image_path")
                    if ip and not os.path.exists(ip):
                        logger.debug("Cache invalidated: missing PNG %s", ip)
                        return None
            return manifest
        except (json.JSONDecodeError, OSError) as e:
            logger.debug("Cache read failed: %s", e)
            return None

    def _save_cache(self, pdf_path: str, result: dict):
        """将提取结果序列化为 JSON manifest（不含 image bytes，仅路径）"""
        cache_path = self._cache_path(pdf_path)
        if cache_path is None:
            return
        try:
            # 仅保存元数据，不保存二进制数据
            serializable = {
                "figures": result["figures"],
                "tables": result["tables"],
                "formulas": result["formulas"],
                "summary": result["summary"],
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False, indent=2)
            logger.debug("VisualExtractor cache saved: %s", cache_path)
        except OSError as e:
            logger.warning("Failed to write cache %s: %s", cache_path, e)

    def _extract_nearby_text(self, page: fitz.Page, bbox: tuple,
                             margin: float = 20) -> str:
        """提取图注/表注：在 bbox 上下 margin 点范围内搜索文本"""
        rect_above = fitz.Rect(bbox[0], max(0, bbox[1] - margin),
                               bbox[2], bbox[1])
        rect_below = fitz.Rect(bbox[0], bbox[3],
                               bbox[2], bbox[3] + margin)
        above = page.get_text("text", clip=rect_above).strip()
        below = page.get_text("text", clip=rect_below).strip()
        return above or below or ""

    def _clean_latex(self, raw: str) -> str:
        """启发式清理可能包含公式的文本"""
        # 如果包含 LaTeX 特征符就保留，否则返回空
        latex_indicators = {"\\", "$", "^{", "_{", "\\frac", "\\sum", "\\int"}
        if any(ind in raw for ind in latex_indicators):
            return raw[:500]
        return raw

    def _build_summary(self, figures: list, tables: list,
                       formulas: list) -> str:
        """生成视觉资产文本摘要（供 LLM OutlineGenerator 使用）

        格式包含资产 ID（如 fig_1, tab_2）以便 LLM 设置 visual_ref。
        """
        parts = []
        if figures:
            items = []
            for f in figures[:10]:
                caption = (f['caption'] or '')[:80]
                items.append(f"[{f['id']}] {caption}")
            parts.append(f"Figures ({len(figures)}): {'; '.join(items)}")
        if tables:
            items = []
            for t in tables[:6]:
                caption = (t['caption'] or '')[:80]
                items.append(f"[{t['id']}] {caption}")
            parts.append(f"Tables ({len(tables)}): {'; '.join(items)}")
        if formulas:
            parts.append(f"Formulas ({len(formulas)}): use [formula_N] to reference")
        if not parts:
            return "No visual assets detected in PDF."
        # 加一行使用指引
        parts.append('When a slide references a specific figure or table, set "visual_ref" to its [id] above.')
        return "\n".join(parts)
