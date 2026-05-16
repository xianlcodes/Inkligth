import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from app.core.config import settings
from app.templates.email import render_template

logger = logging.getLogger(__name__)


def _send_email(to_email: str, subject: str, html_content: str, text_content: str) -> tuple[bool, str]:
    config = sib_api_v3_sdk.Configuration()
    config.api_key["api-key"] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(config))

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"name": settings.BREVO_SENDER_NAME, "email": settings.BREVO_SENDER_EMAIL},
        subject=subject,
        html_content=html_content,
        text_content=text_content,
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Email sent to {to_email}: subject={subject}, message_id={api_response.message_id}")
        return True, ""
    except ApiException as e:
        error_body = str(e.body)[:300] if hasattr(e, 'body') and e.body else str(e)
        logger.error(f"Brevo API error for {to_email}: status={e.status}, body={error_body}")
        return False, f"邮件发送失败: {e.status}"


def send_reset_code_email(to_email: str, code: str) -> tuple[bool, str]:
    if settings.DEV_MODE:
        logger.info(f"[DEV MODE] Password reset code for {to_email}: {code}")
        return True, ""

    html = render_template("reset_code.html", code=code)

    return _send_email(
        to_email=to_email,
        subject="InkLight 密码重置验证码",
        html_content=html,
        text_content=f"您的 InkLight 密码重置验证码是：{code}。有效期 15 分钟。",
    )


def send_verification_email(to_email: str, code: str) -> tuple[bool, str]:
    if settings.DEV_MODE:
        logger.info(f"[DEV MODE] Verification code for {to_email}: {code}")
        return True, ""

    html = render_template("verification_code.html", code=code)

    return _send_email(
        to_email=to_email,
        subject="InkLight 邮箱验证码",
        html_content=html,
        text_content=f"您的 InkLight 邮箱验证码是：{code}。有效期 15 分钟。",
    )
