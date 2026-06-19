"""
Argument Companion 数据访问层（异步）

提供 Ledger、Promise、ReviewSession、ReviewPoint 的 CRUD 操作。
"""

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.argument.models import Ledger, Promise, ReviewSession, ReviewPoint

logger = logging.getLogger(__name__)


# Ledger / Promise

async def get_ledger(db: AsyncSession, ledger_id: str) -> Optional[Ledger]:
    result = await db.execute(select(Ledger).where(Ledger.id == ledger_id))
    return result.scalar_one_or_none()


async def get_ledger_by_literature(db: AsyncSession, literature_id: str, user_id: str) -> Optional[Ledger]:
    result = await db.execute(
        select(Ledger).where(Ledger.literature_id == literature_id, Ledger.user_id == user_id)
        .order_by(desc(Ledger.updated_at)).limit(1)
    )
    return result.scalar_one_or_none()


async def list_ledgers(db: AsyncSession, user_id: str, skip: int = 0, limit: int = 20) -> list[Ledger]:
    result = await db.execute(
        select(Ledger).where(Ledger.user_id == user_id).order_by(desc(Ledger.updated_at)).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def create_ledger(db: AsyncSession, literature_id: str, user_id: str, title: str = "") -> Ledger:
    ledger = Ledger(literature_id=literature_id, user_id=user_id, title=title)
    db.add(ledger)
    await db.commit()
    await db.refresh(ledger)
    logger.info("Created ledger %s for literature %s", ledger.id, literature_id)
    return ledger


async def update_ledger_status(db: AsyncSession, ledger_id: str, status: str, checksum: Optional[str] = None) -> Optional[Ledger]:
    ledger = await get_ledger(db, ledger_id)
    if not ledger:
        return None
    ledger.status = status
    if checksum is not None:
        ledger.checksum = checksum
    ledger.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(ledger)
    return ledger


async def get_promise(db: AsyncSession, promise_id: str) -> Optional[Promise]:
    result = await db.execute(select(Promise).where(Promise.id == promise_id))
    return result.scalar_one_or_none()


async def list_promises(db: AsyncSession, ledger_id: str) -> list[Promise]:
    result = await db.execute(select(Promise).where(Promise.ledger_id == ledger_id).order_by(Promise.created_at))
    return list(result.scalars().all())


async def create_promise(db: AsyncSession, ledger_id: str, user_id: str, claim_text: str,
                         status: str = "unpaid", severity: str = "info",
                         claim_anchor: Optional[dict] = None, claim_section: str = "",
                         discharge_text: str = "", discharge_anchor: Optional[dict] = None) -> Promise:
    promise = Promise(
        ledger_id=ledger_id, user_id=user_id, claim_text=claim_text, status=status, severity=severity,
        claim_anchor=json.dumps(claim_anchor, ensure_ascii=False) if claim_anchor else None,
        claim_section=claim_section, discharge_text=discharge_text,
        discharge_anchor=json.dumps(discharge_anchor, ensure_ascii=False) if discharge_anchor else None,
    )
    db.add(promise)
    await db.commit()
    await db.refresh(promise)
    return promise


async def update_promise_status(db: AsyncSession, promise_id: str, user_status: str, user_overridden: bool = True) -> Optional[Promise]:
    promise = await get_promise(db, promise_id)
    if not promise:
        return None
    promise.user_status = user_status
    promise.user_overridden = user_overridden
    await db.commit()
    await db.refresh(promise)
    return promise


async def delete_promises_by_ledger(db: AsyncSession, ledger_id: str) -> None:
    """删除台账下的所有承诺记录（重建前清理旧数据）"""
    from sqlalchemy import delete as sa_delete
    stmt = sa_delete(Promise).where(Promise.ledger_id == ledger_id)
    await db.execute(stmt)
    await db.commit()
    logger.info("Deleted all promises for ledger %s", ledger_id)


# ReviewSession / ReviewPoint

async def get_review_session(db: AsyncSession, session_id: str) -> Optional[ReviewSession]:
    result = await db.execute(select(ReviewSession).where(ReviewSession.id == session_id))
    return result.scalar_one_or_none()


async def get_review_session_by_literature(db: AsyncSession, literature_id: str, user_id: str) -> Optional[ReviewSession]:
    result = await db.execute(
        select(ReviewSession).where(ReviewSession.literature_id == literature_id, ReviewSession.user_id == user_id)
        .order_by(desc(ReviewSession.updated_at)).limit(1)
    )
    return result.scalar_one_or_none()


async def list_review_sessions(db: AsyncSession, user_id: str, skip: int = 0, limit: int = 20) -> list[ReviewSession]:
    result = await db.execute(
        select(ReviewSession).where(ReviewSession.user_id == user_id).order_by(desc(ReviewSession.updated_at)).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def create_review_session(db: AsyncSession, literature_id: str, user_id: str, mode: str = "parallel") -> ReviewSession:
    session = ReviewSession(literature_id=literature_id, user_id=user_id, mode=mode)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info("Created review session %s for literature %s", session.id, literature_id)
    return session


async def update_review_session(db: AsyncSession, session_id: str, status: Optional[str] = None,
                                 overall_assessment: Optional[str] = None, strengths: Optional[str] = None,
                                 top_issues: Optional[str] = None) -> Optional[ReviewSession]:
    session = await get_review_session(db, session_id)
    if not session:
        return None
    if status is not None:
        session.status = status
    if overall_assessment is not None:
        session.overall_assessment = overall_assessment
    if strengths is not None:
        session.strengths = strengths
    if top_issues is not None:
        session.top_issues = top_issues
    session.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(session)
    return session


async def get_review_point(db: AsyncSession, point_id: str) -> Optional[ReviewPoint]:
    result = await db.execute(select(ReviewPoint).where(ReviewPoint.id == point_id))
    return result.scalar_one_or_none()


async def list_review_points(db: AsyncSession, session_id: str) -> list[ReviewPoint]:
    result = await db.execute(select(ReviewPoint).where(ReviewPoint.session_id == session_id).order_by(ReviewPoint.created_at))
    return list(result.scalars().all())


async def create_review_point(db: AsyncSession, session_id: str, category: str, severity: str,
                               title: str, description: str, suggestion: str = "", anchor_ref: str = "") -> ReviewPoint:
    point = ReviewPoint(session_id=session_id, category=category, severity=severity,
                        title=title, description=description, suggestion=suggestion, anchor_ref=anchor_ref)
    db.add(point)
    await db.commit()
    await db.refresh(point)
    return point


async def update_rebuttal(db: AsyncSession, point_id: str, rebuttal: str, rebuttal_status: str = "pending") -> Optional[ReviewPoint]:
    point = await get_review_point(db, point_id)
    if not point:
        return None
    point.rebuttal = rebuttal
    point.rebuttal_status = rebuttal_status
    await db.commit()
    await db.refresh(point)
    return point


async def update_reviewer_response(db: AsyncSession, point_id: str, reviewer_response: str,
                                    rebuttal_status: str = "addressed") -> Optional[ReviewPoint]:
    point = await get_review_point(db, point_id)
    if not point:
        return None
    point.reviewer_response = reviewer_response
    point.rebuttal_status = rebuttal_status
    await db.commit()
    await db.refresh(point)
    return point

