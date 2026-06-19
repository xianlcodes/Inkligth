from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
import os
import glob as glob_module
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.presentation import (
    PresentationCreate,
    PresentationResponse,
    PresentationListResponse,
)
from app.services.presentation_service import PresentationService

router = APIRouter(prefix="/presentations", tags=["presentations"])


@router.post("", response_model=dict)
async def create_presentation(
    data: PresentationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    presentation = await PresentationService.create_presentation(
        db, str(current_user.id), data
    )
    return {
        "code": 200,
        "msg": "success",
        "data": PresentationResponse.model_validate(presentation).model_dump(mode="json"),
    }


@router.get("", response_model=dict)
async def list_presentations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await PresentationService.get_presentations(
        db, str(current_user.id), limit=limit, offset=offset
    )
    items = [
        PresentationResponse.model_validate(p).model_dump(mode="json")
        for p in result["items"]
    ]
    return {
        "code": 200,
        "msg": "success",
        "data": {"total": result["total"], "items": items},
    }


@router.get("/{presentation_id}", response_model=dict)
async def get_presentation(
    presentation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    presentation = await PresentationService.get_presentation(
        db, presentation_id, str(current_user.id)
    )
    if not presentation:
        raise HTTPException(status_code=404, detail="汇报记录不存在")
    return {
        "code": 200,
        "msg": "success",
        "data": PresentationResponse.model_validate(presentation).model_dump(mode="json"),
    }


@router.delete("/{presentation_id}", response_model=dict)
async def delete_presentation(
    presentation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await PresentationService.delete_presentation(
        db, presentation_id, str(current_user.id)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="汇报记录不存在")
    return {"code": 200, "msg": "success", "data": None}


@router.get("/{presentation_id}/download")
async def download_presentation_ppt(
    presentation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """通过汇报记录 ID 下载 PPT 文件（支持历史记录下载）"""
    presentation = await PresentationService.get_presentation(
        db, presentation_id, str(current_user.id)
    )
    if not presentation:
        raise HTTPException(status_code=404, detail="汇报记录不存在")

    ppt_file_path = getattr(presentation, "ppt_file_path", None)

    # 如果数据库中没有存储路径，尝试在磁盘上搜索（兼容旧记录）
    if not ppt_file_path or not os.path.exists(ppt_file_path):
        output_dir = os.path.join(os.path.abspath(settings.UPLOAD_DIR), "ppt_generated")
        if os.path.isdir(output_dir):
            # 匹配包含 presentation_id 的文件，或匹配文献标题的文件
            safe_name = "".join(c for c in (presentation.literature_title or "") if c.isalnum() or c in "._- ").strip()
            patterns = [
                os.path.join(output_dir, f"{presentation_id}_*.pptx"),
                os.path.join(output_dir, f"*_{safe_name}.pptx") if safe_name else None,
            ]
            for pattern in patterns:
                if pattern:
                    matches = glob_module.glob(pattern)
                    if matches:
                        ppt_file_path = matches[0]
                        # 找到后更新数据库，下次直接命中
                        presentation.ppt_file_path = ppt_file_path
                        await db.commit()
                        break

    if not ppt_file_path or not os.path.exists(ppt_file_path):
        raise HTTPException(status_code=404, detail="PPT 文件不存在或已被清理")

    safe_name = "".join(c for c in (presentation.literature_title or "presentation") if c.isalnum() or c in "._- ").strip()
    filename = f"{safe_name}.pptx"

    return FileResponse(
        path=ppt_file_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )