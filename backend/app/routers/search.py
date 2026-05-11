from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search_literature(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    top_n: int = Query(10, ge=1, le=50, description="返回结果数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = await SearchService.search(db, str(current_user.id), q, top_n)
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "query": q,
            "total": len(results),
            "items": results,
        },
    }