"""
Email service using Resend API.
All send methods are non-fatal: exceptions are logged but never bubble up to callers.
"""
import logging
from typing import Optional

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> bool:
    """Configure the Resend API key. Returns False if key is not set."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured — email will not be sent")
        return False
    resend.api_key = settings.RESEND_API_KEY
    return True


def send_invite_email(
    to_email: str,
    org_name: str,
    org_key: str,
    invite_token: str,
) -> None:
    """Send a church membership invitation email."""
    if not _get_client():
        return

    register_url = (
        f"{settings.FRONTEND_URL}/register"
        f"?org={org_key}&invite={invite_token}"
    )

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #1a3a4a;">You've been invited to join {org_name}</h2>
      <p>You have been invited to take the Gift, Passion, Story (GPS) assessment
         through <strong>{org_name}</strong>.</p>
      <p>Click the button below to create your account and begin your assessment:</p>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{register_url}"
           style="background-color: #1a3a4a; color: white; padding: 14px 28px;
                  text-decoration: none; border-radius: 6px; font-size: 16px;">
          Accept Invitation
        </a>
      </p>
      <p style="color: #666; font-size: 14px;">
        This invitation link expires in 7 days.
        If you did not expect this invitation, you can safely ignore this email.
      </p>
      <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;" />
      <p style="color: #999; font-size: 12px;">
        Gift, Passion, Story Assessment Platform &mdash;
        <a href="{settings.FRONTEND_URL}" style="color: #999;">giftpassionstory.com</a>
      </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": f"You've been invited to join {org_name} on GPS",
            "html": html,
        })
        logger.info("Invite email sent to %s for org %s", to_email, org_name)
    except Exception as exc:
        logger.error("Failed to send invite email to %s: %s", to_email, exc)


def send_password_reset_email(to_email: str, reset_token: str) -> None:
    """Send a password reset email."""
    if not _get_client():
        return

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #1a3a4a;">Reset Your Password</h2>
      <p>We received a request to reset the password for your GPS account.</p>
      <p>Click the button below to choose a new password:</p>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{reset_url}"
           style="background-color: #1a3a4a; color: white; padding: 14px 28px;
                  text-decoration: none; border-radius: 6px; font-size: 16px;">
          Reset Password
        </a>
      </p>
      <p style="color: #666; font-size: 14px;">
        This link expires in 24 hours.
        If you did not request a password reset, you can safely ignore this email —
        your password will not be changed.
      </p>
      <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;" />
      <p style="color: #999; font-size: 12px;">
        Gift, Passion, Story Assessment Platform &mdash;
        <a href="{settings.FRONTEND_URL}" style="color: #999;">giftpassionstory.com</a>
      </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": "Reset your GPS password",
            "html": html,
        })
        logger.info("Password reset email sent to %s", to_email)
    except Exception as exc:
        logger.error("Failed to send password reset email to %s: %s", to_email, exc)
