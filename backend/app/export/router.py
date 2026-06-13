"""
导出系统 API 路由
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_user_db as get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.export.schemas import (
    WordExportRequest,
    LatexExportRequest,
    PdfExportRequest,
    ExportResponse,
    ExportHistoryResponse,
    ExportHistoryItem,
    FileInfo,
)
from app.export.exporter_service import ExportService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["export"])


def _record_to_history_item(record) -> ExportHistoryItem:
    return ExportHistoryItem(
        export_id=record.id,
        format=record.format,
        filename=record.filename,
        source_type=record.source_type,
        file_size=record.file_size or 0,
        created_at=record.created_at,
        download_url=f"/api/v1/export/download/{record.id}",
    )


@router.post("/export/word", response_model=ExportResponse)
async def export_word(
    req: WordExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将笔记/译文/文献导出为 Word 文档"""
    user_id = str(current_user.id)
    try:
        record = await ExportService.create_word_export(
            db=db,
            user_id=user_id,
            source_type=req.source_type,
            source_ids=req.source_ids,
            title=req.title,
            include_toc=req.options.include_toc,
            page_numbers=req.options.page_numbers,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception("Word export failed for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export failed",
        )

    return ExportResponse(
        export_id=record.id,
        format="word",
        filename=record.filename,
        download_url=f"/api/v1/export/download/{record.id}",
        file_size=record.file_size or 0,
        expires_at=record.expires_at,
    )


@router.post("/export/latex", response_model=ExportResponse)
async def export_latex(
    req: LatexExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将笔记/译文/文献导出为 LaTeX 文件"""
    user_id = str(current_user.id)
    try:
        record = await ExportService.create_latex_export(
            db=db,
            user_id=user_id,
            source_type=req.source_type,
            source_ids=req.source_ids,
            title=req.title,
            template=req.options.template,
            authors=req.options.authors,
            abstract=req.options.abstract,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotImplementedError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="LaTeX export requires Pandoc. Please contact the administrator.",
        )
    except Exception:
        logger.exception("LaTeX export failed for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export failed",
        )

    return ExportResponse(
        export_id=record.id,
        format="latex",
        filename=record.filename,
        download_url=f"/api/v1/export/download/{record.id}",
        file_size=record.file_size or 0,
        expires_at=record.expires_at,
    )


@router.post("/export/pdf", response_model=ExportResponse)
async def export_pdf(
    req: PdfExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将笔记/译文/文献导出为 PDF（通过 LaTeX 编译）"""
    user_id = str(current_user.id)
    try:
        record = await ExportService.create_pdf_export(
            db=db,
            user_id=user_id,
            source_type=req.source_type,
            source_ids=req.source_ids,
            title=req.title,
            template=req.options.template,
            authors=req.options.authors,
            abstract=req.options.abstract,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotImplementedError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF export requires Pandoc and a LaTeX compiler (tectonic/latexmk). "
                   "Please contact the administrator.",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception:
        logger.exception("PDF export failed for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export failed",
        )

    compile_log = getattr(record, "_compile_log", None)
    return ExportResponse(
        export_id=record.id,
        format="pdf",
        filename=record.filename,
        download_url=f"/api/v1/export/download/{record.id}",
        file_size=record.file_size or 0,
        compile_log=compile_log,
        expires_at=record.expires_at,
    )


@router.get("/export/download/{export_id}")
async def download_export(
    export_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载导出的文件"""
    user_id = str(current_user.id)
    record = await ExportService.get_user_export(db, user_id, export_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export record not found or expired",
        )

    # 检查文件是否过期
    from datetime import datetime
    if datetime.utcnow() > record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Export file has expired",
        )

    # 检查文件是否存在
    if not os.path.exists(record.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found on disk",
        )

    return FileResponse(
        path=record.file_path,
        filename=record.filename,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{record.filename}"',
        },
    )


@router.get("/export/history", response_model=ExportHistoryResponse)
async def get_export_history(
    format: Optional[str] = Query(None, description="按格式筛选: word | latex | pdf"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取导出历史"""
    total, items = await ExportService.get_export_history(
        db, str(current_user.id), fmt=format, page=page, page_size=page_size,
    )
    return ExportHistoryResponse(
        items=[_record_to_history_item(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )
