"""召回邮件任务（每天北京时间 10:00，总开关默认关闭）。

邮件标题/正文可在管理后台「系统配置」中编辑（recall_*_subject / recall_*_body
四个配置项，HTML 正文），留空时使用内置默认文案。

两种召回：
- no_upload_3d：注册满 3 天还没有登录过 → 引导上传文献 + 提醒免费额度仍在
- inactive_30d：最近一次登录在 30~60 天前 → 唤醒（平台新变化）

防骚扰：每用户每种类型最多发一封（recall_email_logs 记录）；
管理员手动发送走同一防重机制。
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.database import AlibabaSessionLocal
from app.models.user import User
from app.models.recall_email_log import RecallEmailLog

logger = logging.getLogger(__name__)

RECALL_TYPES = ("no_upload_3d", "inactive_30d")

# 内置默认文案（后台未编辑时使用；管理员可在系统配置中直接修改）
_DEFAULT_TEMPLATES = {
    "no_upload_3d": {
        "subject": "你的免费文献翻译额度还在，上传第一篇文献试试",
        "html": """
    <div style="font-family:-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;max-width:560px;margin:0 auto;color:#1e293b;">
      <h2 style="color:#2e7d4f;">hi，欢迎来到研墨</h2>
      <p>你的账号还没有上传过文献。</p>
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
    """,
    },
    "inactive_30d": {
        "subject": "好久不见，研墨的新变化等你回来",
        "html": """
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
    """,
    },
}

# 后台可编辑的 4 个模板配置键
_TEMPLATE_CONFIG_KEYS = {
    "no_upload_3d": ("recall_no_upload_subject", "recall_no_upload_body"),
    "inactive_30d": ("recall_inactive_subject", "recall_inactive_body"),
}

_RECALL_SWITCH_KEY = "recall_emails_enabled"
_INACTIVE_WINDOW_DAYS = 30
_INACTIVE_WINDOW_END_DAYS = 60  # 只扫 30~60 天未登录，避免对长期流失用户每天重复扫描

# 会话工厂模块级可替换（测试用内存库替身）
_session_factory = AlibabaSessionLocal


def _html_to_text(html: str) -> str:
    """粗略把 HTML 转纯文本，作为邮件的 text 兜底内容。"""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</(?:p|div|h[1-6]|li)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def _is_enabled() -> bool:
    """总开关：SystemConfig.recall_emails_enabled == true 时才自动发送（默认关闭）。"""
    from app.models.admin import SystemConfig
    try:
        async with _session_factory() as db:
            row = (
                await db.execute(
                    select(SystemConfig).where(SystemConfig.key == _RECALL_SWITCH_KEY)
                )
            ).scalar_one_or_none()
            return bool(row and str(row.value).strip().lower() == "true")
    except Exception as e:
        logger.warning("召回邮件开关读取失败（视为关闭）: %s", e)
        return False


async def render_recall_email(recall_type: str) -> tuple[str, str, str]:
    """渲染指定类型的邮件，返回 (subject, html, text)。

    标题/正文优先取后台配置（recall_*_subject / recall_*_body），
    未配置或为空时使用内置默认文案。
    """
    if recall_type not in RECALL_TYPES:
        raise ValueError(f"未知的召回类型: {recall_type!r}")

    subject_key, body_key = _TEMPLATE_CONFIG_KEYS[recall_type]
    defaults = _DEFAULT_TEMPLATES[recall_type]

    try:
        subject = (await _get_raw(subject_key)) or defaults["subject"]
        html = (await _get_raw(body_key)) or defaults["html"]
    except Exception as e:
        logger.warning("召回模板读取失败，使用内置默认: %s", e)
        subject, html = defaults["subject"], defaults["html"]

    return subject, html, _html_to_text(html)


async def _get_raw(key: str) -> str | None:
    """读取系统配置原值（不存在/为空 → None）。会话工厂模块级可替换，便于测试。"""
    from app.models.admin import SystemConfig
    async with _session_factory() as db:
        row = (
            await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        ).scalar_one_or_none()
    if row is None or row.value is None or str(row.value).strip() == "":
        return None
    return str(row.value).strip()


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
                # 场景 A：注册满 3 天，从未登录（引导上传文献）
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

                subject, html, text = await render_recall_email(target_type)
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
