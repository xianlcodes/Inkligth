"""
Argument Companion 路由层（异步）

基于 SSE 流式的 API 端点：
  - POST /argument/ledger/build      — 构建承诺台账（流式）
  - GET  /argument/ledger/{id}        — 获取台账详情
  - PUT  /argument/ledger/promise/{id} — 更新承诺状态
  - POST /argument/review/run        — 运行论文评审（流式）
  - GET  /argument/review/{id}        — 获取评审详情
  - POST /argument/review/rebuttal   — 提交答辩
  - POST /argument/review/respond    — 审稿人回复
  - GET  /argument/history            — 历史记录
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.argument import store
from app.argument.ledger import run_ledger_build
from app.argument.reviewer import run_review
from app.argument.schemas import (
    BuildLedgerRequest, LedgerResponse, PromiseResponse, PromiseUpdateRequest,
    ReviewSessionResponse, ReviewPointResponse, RunReviewRequest,
    RebuttalRequest, RebuttalResponse,
)
from app.argument.models import Ledger, ReviewSession
from app.core.ai_client import get_cached_user_ai_client_and_model
from app.core.config import settings
from app.core.deps import get_current_user
from app.db.database import get_tencent_db as get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/argument", tags=["argument"])


async def _create_call_llm(_db: AsyncSession, user_id: str):
    """基于用户配置的 AI 引擎创建异步 call_llm 闭包

    Returns:
        (call_llm_fn, model_name) or (None, None) 如果引擎未配置
    """
    try:
        # AI 引擎配置在阿里云用户数据库上，需要单独的 session
        from app.db.database import AlibabaSessionLocal
        async with AlibabaSessionLocal() as user_db:
            ai_client, model = await get_cached_user_ai_client_and_model(user_db, user_id)
        has_key = bool(ai_client.api_key) and ai_client.api_key != "dummy-key"
        logger.info("AI engine for user %s: model=%s, has_key=%s", user_id, model, has_key)

        if not has_key:
            logger.warning("No valid API key for user %s", user_id)
            return None, None

        async def call_llm(prompt: str, system: str = "") -> str:
            resp = await ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=4096,
            )
            return resp.choices[0].message.content or ""

        return call_llm, model
    except Exception as e:
        logger.warning("Failed to get AI engine for user %s: %s", user_id, e)
        return None, None


# ═══════════════════════════════════════════════════════════
#  承诺台账 (Ledger)
# ═══════════════════════════════════════════════════════════

@router.post("/ledger/build")
async def build_ledger(
    req: BuildLedgerRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """构建承诺台账（SSE 流式）"""
    user_id = user.id

    literature = await _get_literature(db, req.literature_id)
    if not literature:
        raise HTTPException(status_code=404, detail="论文不存在")
    full_text = getattr(literature, "raw_text", "") or ""
    logger.info("build_ledger: literature=%s raw_text length=%d, preview=%s",
                req.literature_id, len(full_text), full_text[:500] if full_text else "")

    # 创建异步 LLM 调用函数
    call_llm, ai_model = await _create_call_llm(db, user_id)
    logger.info("build_ledger: call_llm=%s ai_model=%s", call_llm is not None, ai_model)

    # 获取或创建台账
    ledger = await store.get_ledger_by_literature(db, req.literature_id, user_id)
    if not ledger:
        title = getattr(literature, "title", "")
        ledger = await store.create_ledger(db, req.literature_id, user_id, title=title)

    async def event_generator():
        try:
            if call_llm is None:
                yield {"event": "error", "data": json.dumps({"message": "AI 引擎未配置或 API Key 无效，请在设置中配置后再使用此功能"})}
                await store.update_ledger_status(db, ledger.id, "draft")
                return

            await store.update_ledger_status(db, ledger.id, "building")
            # 重建前清理旧承诺，避免新旧数据混杂
            await store.delete_promises_by_ledger(db, ledger.id)
            yield {"event": "progress", "data": json.dumps({"message": "开始构建承诺台账..."})}

            async for event in run_ledger_build(full_text=full_text, literature_id=req.literature_id, call_llm=call_llm):
                if event.event == "error":
                    yield {"event": "error", "data": json.dumps(event.data)}
                    await store.update_ledger_status(db, ledger.id, "draft")
                    return
                if event.event == "promise_extracted":
                    await store.create_promise(
                        db=db, ledger_id=ledger.id, user_id=user_id,
                        claim_text=event.data.get("claim_text", ""),
                        severity=event.data.get("severity", "info"),
                        claim_section=event.data.get("section_hint", ""),
                    )
                elif event.event == "promise_checked":
                    claim_text = event.data.get("claim_text", "")
                    status = event.data.get("status", "unpaid")
                    discharge = event.data.get("discharge_text", "")
                    for p in await store.list_promises(db, ledger.id):
                        if p.claim_text == claim_text:
                            p.status = status
                            p.discharge_text = discharge
                            await db.commit()
                            break
                yield {"event": event.event, "data": json.dumps(event.data)}

            await store.update_ledger_status(db, ledger.id, "completed")
        except Exception as e:
            logger.exception("Ledger build failed")
            await store.update_ledger_status(db, ledger.id, "draft")
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_generator())


@router.get("/ledger/{ledger_id}", response_model=LedgerResponse)
async def get_ledger(ledger_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    ledger = await store.get_ledger(db, ledger_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="台账不存在")
    if ledger.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问")
    return _ledger_to_response(ledger, await store.list_promises(db, ledger_id))


@router.get("/ledger/by-lit/{literature_id}", response_model=Optional[LedgerResponse])
async def get_ledger_by_literature(literature_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    ledger = await store.get_ledger_by_literature(db, literature_id, user.id)
    if not ledger:
        return None
    return _ledger_to_response(ledger, await store.list_promises(db, ledger.id))


@router.put("/ledger/promise/{promise_id}")
async def update_promise(promise_id: str, req: PromiseUpdateRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    promise = await store.update_promise_status(db, promise_id, user_status=req.user_status, user_overridden=req.user_overridden)
    if not promise:
        raise HTTPException(status_code=404, detail="承诺不存在")
    return {"status": "ok", "promise_id": promise_id, "new_status": req.user_status}


# ═══════════════════════════════════════════════════════════
#  论文评审 (Review)
# ═══════════════════════════════════════════════════════════

@router.post("/review/run")
async def run_review_endpoint(
    req: RunReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    user_id = user.id
    literature = await _get_literature(db, req.literature_id)
    if not literature:
        raise HTTPException(status_code=404, detail="论文不存在")
    full_text = getattr(literature, "raw_text", "") or ""

    # 创建异步 LLM 调用函数
    call_llm, ai_model = await _create_call_llm(db, user_id)

    session = await store.create_review_session(db, req.literature_id, user_id, mode=req.mode)

    async def event_generator():
        try:
            if call_llm is None:
                yield {"event": "error", "data": json.dumps({"message": "AI 引擎未配置或 API Key 无效，请在设置中配置后再使用此功能"})}
                await store.update_review_session(db, session.id, status="draft")
                return

            await store.update_review_session(db, session.id, status="running")
            yield {"event": "progress", "data": json.dumps({"message": "开始论文评审..."})}

            async for event in run_review(full_text=full_text, perspectives=req.perspectives, max_points_per_perspective=5, call_llm=call_llm):
                if event.event == "error":
                    yield {"event": "error", "data": json.dumps(event.data)}
                    await store.update_review_session(db, session.id, status="draft")
                    return
                if event.event == "review_point":
                    d = event.data
                    await store.create_review_point(db=db, session_id=session.id,
                        category=d.get("category", ""), severity=d.get("severity", "minor"),
                        title=d.get("title", ""), description=d.get("description", ""),
                        suggestion=d.get("suggestion", ""), anchor_ref=d.get("anchor_ref", ""))
                elif event.event == "assessment":
                    d = event.data
                    await store.update_review_session(db, session.id, status="completed",
                        overall_assessment=d.get("overall_assessment", ""),
                        strengths=d.get("strengths", ""), top_issues=d.get("top_issues", ""))
                yield {"event": event.event, "data": json.dumps(event.data)}
        except Exception as e:
            logger.exception("Review failed")
            await store.update_review_session(db, session.id, status="draft")
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_generator())


@router.get("/review/{session_id}", response_model=ReviewSessionResponse)
async def get_review(session_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    session = await store.get_review_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="评审会话不存在")
    return _review_session_to_response(session, await store.list_review_points(db, session_id))


@router.get("/review/by-lit/{literature_id}", response_model=Optional[ReviewSessionResponse])
async def get_review_by_literature(literature_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    session = await store.get_review_session_by_literature(db, literature_id, user.id)
    if not session:
        return None
    return _review_session_to_response(session, await store.list_review_points(db, session.id))


# ═══════════════════════════════════════════════════════════
#  答辩 (Rebuttal)
# ═══════════════════════════════════════════════════════════

@router.post("/review/rebuttal", response_model=RebuttalResponse)
async def submit_rebuttal(req: RebuttalRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    point = await store.update_rebuttal(db, req.point_id, rebuttal=req.message, rebuttal_status="pending")
    if not point:
        raise HTTPException(status_code=404, detail="评审点不存在")
    return RebuttalResponse(point_id=req.point_id, session_id=req.session_id, rebuttal_status="pending", reviewer_response=None)


@router.post("/review/respond", response_model=RebuttalResponse)
async def reviewer_respond(req: RebuttalRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    point = await store.update_reviewer_response(db, req.point_id, reviewer_response=req.message, rebuttal_status="addressed")
    if not point:
        raise HTTPException(status_code=404, detail="评审点不存在")
    return RebuttalResponse(point_id=req.point_id, session_id=req.session_id, rebuttal_status="addressed", reviewer_response=req.message)


# ═══════════════════════════════════════════════════════════
#  历史记录
# ═══════════════════════════════════════════════════════════

@router.get("/history")
async def get_history(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
                       skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    ledgers = await store.list_ledgers(db, user.id, skip=skip, limit=limit)
    sessions = await store.list_review_sessions(db, user.id, skip=skip, limit=limit)
    return {"ledgers": [_ledger_summary(l) for l in ledgers], "review_sessions": [_review_session_summary(s) for s in sessions]}


# ═══════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════

async def _get_literature(db: AsyncSession, literature_id: str):
    try:
        from app.models.literature import Literature
        from sqlalchemy import select
        result = await db.execute(select(Literature).where(Literature.id == literature_id))
        return result.scalar_one_or_none()
    except Exception:
        logger.warning("Literature model not available, using mock")
        return None


def _ledger_to_response(ledger: Ledger, promises: list) -> LedgerResponse:
    return LedgerResponse(
        id=ledger.id, literature_id=ledger.literature_id, title=ledger.title,
        status=ledger.status, checksum=ledger.checksum,
        promises=[_promise_to_response(p) for p in promises],
        created_at=ledger.created_at, updated_at=ledger.updated_at,
    )


def _promise_to_response(promise) -> PromiseResponse:
    return PromiseResponse(
        id=promise.id, claim_text=promise.claim_text, claim_anchor=promise.claim_anchor,
        claim_section=promise.claim_section, status=promise.status, severity=promise.severity,
        discharge_text=promise.discharge_text, discharge_anchor=promise.discharge_anchor,
        user_overridden=promise.user_overridden, user_status=promise.user_status,
        created_at=promise.created_at,
    )


def _review_session_to_response(session: ReviewSession, points: list) -> ReviewSessionResponse:
    return ReviewSessionResponse(
        id=session.id, literature_id=session.literature_id, mode=session.mode,
        status=session.status, overall_assessment=session.overall_assessment,
        strengths=session.strengths, top_issues=session.top_issues,
        points=[_review_point_to_response(p) for p in points],
        created_at=session.created_at, updated_at=session.updated_at,
    )


def _review_point_to_response(point) -> ReviewPointResponse:
    return ReviewPointResponse(
        id=point.id, category=point.category, severity=point.severity,
        title=point.title, description=point.description, suggestion=point.suggestion,
        anchor_ref=point.anchor_ref, rebuttal=point.rebuttal,
        rebuttal_status=point.rebuttal_status, reviewer_response=point.reviewer_response,
        created_at=point.created_at,
    )


def _ledger_summary(ledger: Ledger) -> dict:
    return {
        "id": ledger.id, "literature_id": ledger.literature_id, "title": ledger.title,
        "status": ledger.status,
        "created_at": ledger.created_at.isoformat() if ledger.created_at else None,
        "updated_at": ledger.updated_at.isoformat() if ledger.updated_at else None,
    }


def _review_session_summary(session: ReviewSession) -> dict:
    return {
        "id": session.id, "literature_id": session.literature_id, "mode": session.mode,
        "status": session.status, "overall_assessment": session.overall_assessment,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }
