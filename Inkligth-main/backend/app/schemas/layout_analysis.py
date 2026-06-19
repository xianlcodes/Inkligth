from pydantic import BaseModel, Field
from typing import Optional


class LayoutBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float
    class_id: int
    class_name: str


class LayoutRegion(BaseModel):
    class_name: str
    boxes: list[LayoutBox]


class PageLayoutResult(BaseModel):
    page_number: int
    page_width: float
    page_height: float
    regions: list[LayoutRegion] = Field(default_factory=list)
    layout_mask_shape: Optional[tuple[int, int]] = None


class LayoutAnalysisRequest(BaseModel):
    literature_id: str
    pages: Optional[list[int]] = None


class LayoutAnalysisResponse(BaseModel):
    literature_id: str
    total_pages: int
    page_results: list[PageLayoutResult]
    model_config = {"protected_namespaces": ()}
    model_info: Optional[str] = None
    backend: Optional[str] = None


class LayoutAnalysisStatus(BaseModel):
    ready: bool
    model_config = {"protected_namespaces": ()}
    model_path: Optional[str] = None
    backend: Optional[str] = None
    available_providers: list[str] = Field(default_factory=list)