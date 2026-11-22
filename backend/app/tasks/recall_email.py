"""召回邮件任务（每天北京时间 10:00，默认关闭）。

两种召回：
- no_upload_3d：注册满 3 天但还没上传任何文献 → 引导上传文献 + 提醒免费额度仍在
- inactive_30d：最近一次登录在 30~60 天前 → 唤醒（平台新功能/免费额度）

防骚扰机制：
- 每个用户每种类型最多发一次（recall_email_logs 表记录）；
- 总开关为 SystemConfig 的 recall_emails_enabled（默认缺失=关闭），
  管理员可在「系统配置」页添加该配置并设为 true 开启。
"""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.database import AlibabaSessionLocal
from app.models.user import User
from app.models.recall_email_log import RecallEmailLog

logger = logging.getLogger(__name__)

_RECALL_SWITCH_KEY = "recall_emails_enabled"
_INACTIVE_WINDOW_DAYS = 30
_INACTIVE_WINDOW_END_DAYS = 60  # 只扫 30~60 天未登录，避免对长期流失用户每天重复扫描


async def _is_enabled() -> bool:
    """总开关：SystemConfig.recall_emails_enabled == true 时才发信（默认关闭）。"""
    from app.models.admin import SystemConfig
    try:
        async with AlibabaSessionLocal() as db:
            row = (
                await db.execute(
                    select(SystemConfig).where(SystemConfig.key == _RECALL_SWITCH_KEY)
                )
            ).scalar_one_or_none()
            return bool(row and str(row.value).strip().lower() == "true")
    except Exception as e:
        logger.warning("召回邮件开关读取失败（视为关闭）: %s", e)
        return False


async def _already_sent(db, user_id: str, recall_type: str) -> bool:
    row = (
        await db.execute(
            select(RecallEmailLog.id).where(
                RecallEmailLog.user_id == user_id,
                RecallEmailLog.recall_type == recall_type,
            )
        )
    ).first()
    return row is not None


def _render_no_upload(email: str) -> tuple[str, str, str]:
    subject = "你的免费文献翻译额度还在，上传第一篇文献试试"
    html = f"""
    <div style="font-family:-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;max-width:560px;margin:0 auto;color:#1e293b;">
      <h2 style="color:#2e7d4f;"> hi，{email}</h2>
      <p>你在研墨的账号还没有上传过文献。</p>
      <p>账号里赠送的 <strong>1 篇文献免费翻译额度</strong> 仍然有效——上传一篇 PDF，
      就能得到保留原排版的双语对照译文。</p>
      <p style="margin:24px 0;">
        <a href="https://www.inklight.cn/literature"
           style="background:#2e7d4f;color:#fff;padding:10px 22px;border-radius:8px;text-decoration:none;">
          上传文献并翻译
        </a>
      </p>
      <p style="color:#64748b;font-size:13px;">如果不想再收到此类邮件，请回复本邮件告知，我们会为你关闭。</p>
    </div>
    """
    text = f"你的免费文献翻译额度还在。上传第一篇文献开始使用：https://www.inklight.cn/literature"
    return subject, html, text


def _render_inactive(email: str) -> tuple[str, str, str]:
    subject = "好久不见，研墨的新变化等你回来"
    html = f"""
    <div style="font-family:-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;max-width:560px;margin:0 auto;color:#1e293b;">
      <h2 style="color:#2e7d4f;">好久不见</h2>
      <p>你已经有一段时间没有登录研墨了。</p>
      <p>这阵子我们改进了文献翻译（保留原排版的双语对照）、AI 精读问答和组会 PPT 生成，
      上传一篇 PDF 就能直接用。</p>
      <p style="margin:24px 0;">
        <a href="https://www.inklight.cn/dashboard"
           style="background:#2e7d4f;color:#fff;padding:10px 22px;border-radius:8px;text-decoration:none;">
          回到研墨
        </a>
      </p>
      <p style="color:#64748b;font-size:13px;">如果不想再收到此类邮件，请回复本邮件告知，我们会为你关闭。</p>
    </div>
    """
    text = "好久不见，回到研墨继续你的文献阅读：https://www.inklight.cn/dashboard"
    return subject, html, text


async def run_recall_emails() -> None:
    """执行一轮召回扫描与发送（由调度器每天 10:00 调用）。"""
    if not await _is_enabled():
        logger.info("召回邮件未开启（SystemConfig: recall_emails_enabled != true），跳过")
        return

    from app.services.email_service import _send_email

    now = datetime.utcnow()
    sent = skipped = failed = 0

    async with AlibabaSessionLocal() as db:
        users = (
            await db.execute(select(User).where(User.is_admin.is_(False)))
        ).scalars().all()

        for user in users:
            try:
                target_type = None
                # 场景 A：注册满 3 天，没有任何文献（无文献信息在此库，改为仅按注册时间 + 未登录过粗筛）
                created_3d_ago = user.created_at and (now - user.created_at) >= timedelta(days=3)
                never_logged = not user.last_login_at
                if created_3d_ago and never_logged and not await _already_sent(db, user.id, "no_upload_3d"):
                    target_type = "no_upload_3d"
                # 场景 B：30~60 天未登录
                elif (
                    user.last_login_at
                    and timedelta(days=_INACTIVE_WINDOW_DAYS) <= (now - user.last_login_at) <= timedelta(days=_INACTIVE_WINDOW_END_DAYS)
                    and not await _already_sent(db, user.id, "inactive_30d")
                ):
                    target_type = "inactive_30d"

                if not target_type:
                    skipped += 1
                    continue

                if target_type == "no_upload_3d":
                    subject, html, text = _render_no_upload(user.email or "")
                else:
                    subject, html, text = _render_inactive(user.email or "")

                # _send_email 是同步 Brevo 调用，放线程池避免阻塞事件循环
                ok, msg = await asyncio.to_thread(_send_email, user.email, subject, html, text)
                if ok:
                    db.add(RecallEmailLog(user_id=str(user.id), recall_type=target_type))
                    await db.commit()
                    sent += 1
                else:
                    failed += 1
                    logger.warning("召回邮件发送失败 user=%s: %s", user.id, msg)
            except Exception as e:
                failed += 1
                logger.error("召回邮件处理异常 user=%s: %s", user.id, e)

    logger.info("召回邮件轮次完成: 发送=%d 跳过=%d 失败=%d", sent, skipped, failed)
