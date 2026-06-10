from enum import Enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    WORD = "word"
    LATEX = "latex"
    PDF = "pdf"


class ExportSource(str, Enum):
    NOTE = "note"
    TRANSLATION = "translation"
    LITERATURE = "literature"


# ── Word 导出 ──

class WordExportOptions(BaseModel):
    include_toc: bool = False
    page_numbers: bool = True


class WordExportRequest(BaseModel):
    source_type: str = Field(..., pattern="^(note|translation|literature)$")
    source_ids: list[str] = Field(..., min_length=1, max_length=50)
    title: str = "InkLight Export"
    options: WordExportOptions = WordExportOptions()


# ── LaTeX 导出 ──

class LatexExportOptions(BaseModel):
    template: str = Field(default="generic", pattern="^(ieee|acm|neurips|lncs|generic)$")
    authors: list[str] = []
    abstract: str = ""


class LatexExportRequest(BaseModel):
    source_type: str = Field(..., pattern="^(note|translation|literature)$")
    source_ids: list[str] = Field(..., min_length=1, max_length=50)
    title: str = "InkLight Export"
    options: LatexExportOptions = LatexExportOptions()


# ── PDF 导出 ──

class PdfExportRequest(BaseModel):
    source_type: str = Field(..., pattern="^(note|translation|literature)$")
    source_ids: list[str] = Field(..., min_length=1, max_length=50)
    title: str = "InkLight Export"
    options: LatexExportOptions = LatexExportOptions()


# ── 响应 ──

class FileInfo(BaseModel):
    name: str
    url: str
    size: int


class ExportResponse(BaseModel):
    export_id: str
    format: str
    filename: str
    download_url: str
    files: list[FileInfo] = []
    compile_log: Optional[str] = None
    file_size: int = 0
    expires_at: datetime


class ExportHistoryItem(BaseModel):
    export_id: str
    format: str
    filename: str
    source_type: str
    file_size: int
    created_at: datetime
    download_url: str

    class Config:
        from_attributes = True


class ExportHistoryResponse(BaseModel):
    items: list[ExportHistoryItem]
    total: int
    page: int
    page_size: int
