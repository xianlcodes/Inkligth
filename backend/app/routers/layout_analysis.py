import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.literature import Literature
from app.schemas.layout_analysis import (
    LayoutAnalysisRequest,
    LayoutAnalysisResponse,
    LayoutAnalysisStatus,
    PageLayoutResult,
)
from app.services.layout_analysis_service import layout_analysis_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["layout-analysis"])


def _resolve_file_path(file_path: str) -> str:
    if os.path.isabs(file_path) and os.path.exists(file_path):
        return file_path

    upload_dir = os.path.abspath(settings.UPLOAD_DIR)

    if not os.path.isabs(file_path):
        candidate = os.path.join(upload_dir, os.path.basename(file_path))
        if os.path.exists(candidate):
            return candidate

        candidate = os.path.join(upload_dir, file_path)
        if os.path.exists(candidate):
            return candidate

    return os.path.join(upload_dir, os.path.basename(file_path))


@router.get("/status", response_model=LayoutAnalysisStatus)
async def get_layout_analysis_status():
    return LayoutAnalysisStatus(
        ready=layout_analysis_service.is_ready,
        model_path=layout_analysis_service.model_path,
        backend=layout_analysis_service.backend,
        available_providers=layout_analysis_service.available_providers,
    )


@router.post("/init")
async def initialize_layout_model(
    backend: str = "cpu",
):
    if backend not in ("cpu", "cuda", "dml"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid backend: {backend}. Choose from: cpu, cuda, dml"
        )
    try:
        layout_analysis_service.set_backend(backend)
        layout_analysis_service.load_model(force_reload=True)
        return {
            "code": 200,
            "msg": "Layout analysis model initialized successfully",
            "data": {
                "backend": layout_analysis_service.backend,
                "model_path": layout_analysis_service.model_path,
                "providers": layout_analysis_service.available_providers,
            }
        }
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to initialize layout model: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize layout model: {e}"
        )


@router.post("/analyze", response_model=LayoutAnalysisResponse)
async def analyze_layout(
    req: LayoutAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    literature = await db.get(Literature, req.literature_id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")
    if str(literature.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此文献")

    file_path = _resolve_file_path(literature.file_path)
    import os
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献文件不存在")

    try:
        if not layout_analysis_service.is_ready:
            layout_analysis_service.load_model()

        results = layout_analysis_service.analyze_document(
            doc_path=file_path,
            pages=req.pages,
        )

        return LayoutAnalysisResponse(
            literature_id=req.literature_id,
            total_pages=len(results),
            page_results=results,
            model_info=layout_analysis_service.model_path,
            backend=layout_analysis_service.backend,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Layout model not available: {e}"
        )
    except Exception as e:
        logger.error("Layout analysis failed for literature %s: %s", req.literature_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Layout analysis failed: {e}"
        )


@router.get("/analyze/{literature_id}/page/{page_number}", response_model=PageLayoutResult)
async def analyze_single_page(
    literature_id: str,
    page_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    literature = await db.get(Literature, literature_id)
    if not literature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献不存在")
    if str(literature.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此文献")

    file_path = _resolve_file_path(literature.file_path)
    import os
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文献文件不存在")

    try:
        if not layout_analysis_service.is_ready:
            layout_analysis_service.load_model()

        results = layout_analysis_service.analyze_document(
            doc_path=file_path,
            pages=[page_number],
        )
        if not results:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="页面不存在")
        return results[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Single page analysis failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Page analysis failed: {e}"
        )