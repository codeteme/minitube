"""Outbound email for password reset using FastAPI-Mail."""
import logging
import os

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

logger = logging.getLogger(__name__)


def _mail_settings() -> dict[str, str | int | bool | None]:
    return {
        "MAIL_USERNAME": os.getenv("MAIL_USERNAME"),
        "MAIL_PASSWORD": os.getenv("MAIL_PASSWORD"),
        "MAIL_FROM": os.getenv("MAIL_FROM"),
        "MAIL_PORT": int(os.getenv("MAIL_PORT", 587)),
        "MAIL_SERVER": os.getenv("MAIL_SERVER"),
        "MAIL_STARTTLS": os.getenv("MAIL_STARTTLS") == "True",
        "MAIL_SSL_TLS": os.getenv("MAIL_SSL_TLS") == "True",
        "USE_CREDENTIALS": True,
        "VALIDATE_CERTS": True,
    }


def _get_mail_config() -> ConnectionConfig | None:
    settings = _mail_settings()
    required_fields = ("MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_FROM", "MAIL_SERVER")
    missing_fields = [field for field in required_fields if not settings[field]]
    if missing_fields:
        logger.warning(
            "Password reset email skipped because mail settings are missing: %s",
            ", ".join(missing_fields),
        )
        return None
    return ConnectionConfig(**settings)

def _frontend_base_url() -> str:
    return os.getenv("FRONTEND_BASE_URL", "http://localhost:5173").strip().rstrip("/")


async def send_reset_email(recipient_email: str, token: str) -> None:
    """Send an HTML email with a link to the frontend reset-password page.
    Args:
        recipient_email: Address to deliver the message to.
        token: Opaque reset JWT appended to the reset URL query string.
    The link uses ``FRONTEND_BASE_URL`` (default ``http://localhost:5173`` for local dev),
    e.g. ``<base>/reset-password?token=...``.
    """
    base = _frontend_base_url()
    reset_link = f"{base}/reset-password?token={token}"
    html_content = f"""
    <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>You requested a password reset. Click the link below to set a new password:</p>
            <p><a href="{reset_link}">Reset My Password</a></p>
            <p>If you did not request this, please ignore this email.</p>
        </body>
    </html>
    """
    message = MessageSchema(
        subject="Reset Your Password",
        recipients=[recipient_email],
        body=html_content,
        subtype=MessageType.html,
    )
    conf = _get_mail_config()
    if conf is None:
        return
    fm = FastMail(conf)
    await fm.send_message(message)
