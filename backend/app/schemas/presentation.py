import json
from pydantic import BaseModel, field_validator
from typing import Optional, List, Any
from datetime import datetime


class SlideData(BaseModel):
    """单个幻灯片数据 — 向后兼容，新增字段皆为可选"""
    title: str
    bullets: List[str] = []
    notes: Optional[str] = None

    # 专业 PPT 扩展字段
    page_type: str = "bullet_text"
    # "title" | "section_header" | "bullet_text" | "dual_column"
    # | "figure_full" | "figure_text" | "comparison_table"
    # | "formula_derivation" | "data_chart" | "timeline"
    visual_ref: Optional[str] = None       # 视觉资产 ID
    suggested_chart: Optional[str] = None   # 图表类型
    chart_data_hint: Optional[Any] = None   # 图表数据（str描述或结构化dict）

    @field_validator("chart_data_hint", mode="before")
    @classmethod
    def coerce_chart_data_hint(cls, v: Any) -> Optional[str]:
        """LLM 可能返回 dict，统一转为 JSON 字符串"""
        if v is None:
            return None
        if isinstance(v, str):
            return v
        try:
            return json.dumps(v, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(v)


class PptxGenerateRequest(BaseModel):
    """专业 PPT 生成请求"""
    theme: str = "cs"                      # 学科主题
    custom_slides: Optional[List[SlideData]] = None  # 自定义大纲


class PresentationCreate(BaseModel):
    literature_id: str
    literature_title: Optional[str] = None
    slides: List[SlideData] = []


class PresentationResponse(BaseModel):
    id: str
    literature_id: Optional[str] = None
    literature_title: Optional[str] = None
    slides: List[SlideData] = []
    slide_count: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PresentationListResponse(BaseModel):
    total: int
    items: List[PresentationResponse]


# ── 视觉资产 Schemas ──

class VisualAsset(BaseModel):
    """PDF 中提取的视觉元素"""
    id: str
    asset_type: str   # "figure" | "table" | "formula"
    page_number: int
    caption: Optional[str] = None
    image_path: Optional[str] = None
    table_data: Optional[List[List[str]]] = None
    latex_raw: Optional[str] = None
    alt_text: Optional[str] = None       # VLM 或启发式描述


class VisualAssetList(BaseModel):
    figures: List[VisualAsset] = []
    tables: List[VisualAsset] = []
    formulas: List[VisualAsset] = []
    summary: str = ""
