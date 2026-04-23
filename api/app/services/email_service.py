"""
Email service using Resend API.
All send methods are non-fatal: exceptions are logged but never bubble up to callers.
"""
import logging
from typing import Optional

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)

# Domains that will always bounce — skip sending to protect sender reputation.
_BLOCKED_DOMAINS: set[str] = {
    "example.com",
    "example.org",
    "example.net",
    "test.com",
    "test.org",
    "testing.com",
    "mailinator.com",
    "guerrillamail.com",
    "tempmail.com",
    "throwaway.email",
    "fakeinbox.com",
    "sharklasers.com",
    "guerrillamailblock.com",
    "grr.la",
    "dispostable.com",
    "yopmail.com",
    "trashmail.com",
    "tempail.com",
    "localhost",
    "invalid",
}


def _is_blocked_email(email: str) -> bool:
    """Return True if the email belongs to a known test/disposable domain."""
    domain = email.rsplit("@", 1)[-1].lower()
    return domain in _BLOCKED_DOMAINS


def _get_client() -> bool:
    """Configure the Resend API key. Returns False if key is not set."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured — email will not be sent")
        return False
    resend.api_key = settings.RESEND_API_KEY
    return True


def send_verification_email(to_email: str, first_name: str, verification_token: str) -> None:
    """Send an email verification link to a newly registered user."""
    if not _get_client():
        return
    if _is_blocked_email(to_email):
        logger.info("Skipped email to blocked/test address: %s", to_email)
        return

    verify_url = f"{settings.FRONTEND_URL}/verify-email/confirm?token={verification_token}"
    greeting = first_name or "there"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #1a3a4a;">Verify Your Email Address</h2>
      <p>Hi {greeting},</p>
      <p>Thanks for creating your GPS account! Please verify your email address
         by clicking the button below:</p>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{verify_url}"
           style="background-color: #1a3a4a; color: white; padding: 14px 28px;
                  text-decoration: none; border-radius: 6px; font-size: 16px;">
          Verify Email
        </a>
      </p>
      <p style="color: #666; font-size: 14px;">
        This link expires in 24 hours.
        If you did not create an account, you can safely ignore this email.
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
            "subject": "Verify your email address — GPS",
            "html": html,
        })
        logger.info("Verification email sent to %s", to_email)
    except Exception as exc:
        logger.error("Failed to send verification email to %s: %s", to_email, exc)


def send_invite_email(
    to_email: str,
    org_name: str,
    org_key: str,
    invite_token: str,
) -> None:
    """Send a church membership invitation email."""
    if not _get_client():
        return
    if _is_blocked_email(to_email):
        logger.info("Skipped email to blocked/test address: %s", to_email)
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


def send_assessment_notification_email(
    to_email: str,
    admin_name: str,
    member_name: str,
    org_name: str,
    instrument_type: str,
    dashboard_url: str,
) -> None:
    """Notify a church admin that a member has completed an assessment."""
    if not _get_client():
        return
    if _is_blocked_email(to_email):
        logger.info("Skipped email to blocked/test address: %s", to_email)
        return

    instrument_label = "MyImpact" if instrument_type == "myimpact" else "GPS"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #1a3a4a;">New Assessment Completed at {org_name}</h2>
      <p>Hi {admin_name},</p>
      <p><strong>{member_name}</strong> just completed a <strong>{instrument_label}</strong>
         assessment through {org_name}.</p>
      <p>View their results in your admin dashboard:</p>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{dashboard_url}"
           style="background-color: #1a3a4a; color: white; padding: 14px 28px;
                  text-decoration: none; border-radius: 6px; font-size: 16px;">
          View Dashboard
        </a>
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
            "subject": f"New assessment completed at {org_name}",
            "html": html,
        })
        logger.info(
            "Assessment notification sent to %s for member %s at org %s",
            to_email, member_name, org_name,
        )
    except Exception as exc:
        logger.error("Failed to send assessment notification to %s: %s", to_email, exc)


def send_gps_result_email(to_email: str, first_name: str, result, results_url: str = "") -> None:
    """Send a user their GPS assessment results."""
    if not _get_client():
        return
    if _is_blocked_email(to_email):
        logger.info("Skipped email to blocked/test address: %s", to_email)
        return

    def _gift_card(name, description, score, bg):
        bar_pct = min(int(score), 100) if score else 0
        return f"""
        <div style="margin-bottom:16px; border-radius:8px; overflow:hidden; border:1px solid #e0e0e0;">
          <div style="background:{bg}; padding:12px 16px; display:flex; align-items:center; justify-content:space-between;">
            <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:16px; color:#ffffff;">{name or '—'}</span>
            <span style="font-family:Arial,sans-serif; font-size:14px; color:#ffffff; opacity:0.9;">Score: {score or 0}</span>
          </div>
          <div style="padding:12px 16px; background:#ffffff;">
            <div style="background:#f0f0f0; border-radius:4px; height:8px; margin-bottom:8px;">
              <div style="background:{bg}; border-radius:4px; height:8px; width:{bar_pct}%;"></div>
            </div>
            <p style="font-family:Arial,sans-serif; font-size:14px; color:#3F4644; margin:0;">{description or ''}</p>
          </div>
        </div>"""

    def _passion_card(name, description, bg):
        return f"""
        <div style="margin-bottom:12px; border-radius:8px; overflow:hidden; border:1px solid #e0e0e0;">
          <div style="background:{bg}; padding:10px 16px;">
            <span style="font-family:Arial,sans-serif; font-weight:bold; font-size:15px; color:#ffffff;">{name or '—'}</span>
          </div>
          <div style="padding:10px 16px; background:#ffffff;">
            <p style="font-family:Arial,sans-serif; font-size:14px; color:#3F4644; margin:0;">{description or ''}</p>
          </div>
        </div>"""

    def _tag_list(items, bg):
        tags = "".join(
            f'<span style="display:inline-block; background:{bg}; border-radius:20px; padding:4px 12px; margin:4px; font-family:Arial,sans-serif; font-size:13px; color:#ffffff;">{item.strip()}</span>'
            for item in items if item.strip()
        )
        return tags or '<span style="color:#aaa; font-size:13px;">None listed</span>'

    gifts_html = "".join([
        _gift_card(getattr(result, f'gift_{i}_name', None),
                   getattr(result, f'gift_{i}_description', None),
                   getattr(result, f'spiritual_gift_{i}_score', None),
                   "#0B6C80")
        for i in range(1, 5)
        if getattr(result, f'gift_{i}_name', None)
    ])

    passions_html = "".join([
        _passion_card(getattr(result, f'passion_{i}_name', None),
                      getattr(result, f'passion_{i}_description', None),
                      "#F7A824")
        for i in range(1, 4)
        if getattr(result, f'passion_{i}_name', None)
    ])

    abilities_tags = _tag_list(getattr(result, 'abilities_list', []) or [], "#7C6FAB")
    people_tags = _tag_list(getattr(result, 'people_list', []) or [], "#E3A2A2")
    cause_tags = _tag_list(getattr(result, 'cause_list', []) or [], "#0B6C80")

    cta_url = results_url or f"{settings.FRONTEND_URL}/dashboard"

    html = f"""
    <div style="font-family:Arial,sans-serif; max-width:620px; margin:0 auto; color:#3F4644;">
      <div style="background:#1a3a4a; padding:32px 24px; border-radius:8px 8px 0 0; text-align:center;">
        <h1 style="color:#ffffff; margin:0; font-size:24px;">Your GPS Results, {first_name}!</h1>
        <p style="color:#88C0C3; margin:8px 0 0; font-size:15px;">Gift &bull; Passion &bull; Story</p>
      </div>
      <div style="background:#f9f9f9; padding:24px; border-radius:0 0 8px 8px; border:1px solid #e0e0e0; border-top:none;">

        <h2 style="color:#0B6C80; font-size:20px; margin:0 0 16px;">Your Top Spiritual Gifts</h2>
        {gifts_html}

        <h2 style="color:#F7A824; font-size:20px; margin:24px 0 16px;">Your Influencing Styles</h2>
        {passions_html}

        <h2 style="color:#3F4644; font-size:20px; margin:24px 0 12px;">Your Selections</h2>
        <p style="font-size:13px; font-weight:bold; color:#7C6FAB; margin:8px 0 4px;">KEY ABILITIES</p>
        <div style="margin-bottom:12px;">{abilities_tags}</div>
        <p style="font-size:13px; font-weight:bold; color:#E3A2A2; margin:8px 0 4px;">PEOPLE YOU'RE PASSIONATE ABOUT</p>
        <div style="margin-bottom:12px;">{people_tags}</div>
        <p style="font-size:13px; font-weight:bold; color:#0B6C80; margin:8px 0 4px;">CAUSES YOU CARE ABOUT</p>
        <div style="margin-bottom:24px;">{cause_tags}</div>

        <p style="text-align:center; margin:32px 0 0;">
          <a href="{cta_url}"
             style="background:#0B6C80; color:#ffffff; padding:14px 32px; text-decoration:none;
                    border-radius:6px; font-size:16px; font-weight:bold;">
            View Full Results
          </a>
        </p>
        <hr style="border:none; border-top:1px solid #eee; margin:32px 0;" />
        <p style="color:#999; font-size:12px; text-align:center;">
          Gift, Passion, Story Assessment Platform &mdash;
          <a href="{settings.FRONTEND_URL}" style="color:#999;">giftpassionstory.com</a>
        </p>
      </div>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": "Your GPS Assessment Results",
            "html": html,
        })
        logger.info("GPS result email sent to %s", to_email)
    except Exception as exc:
        logger.error("Failed to send GPS result email to %s: %s", to_email, exc)


def send_myimpact_result_email(to_email: str, first_name: str, result, results_url: str = "") -> None:
    """Send a user their MyImpact assessment results."""
    if not _get_client():
        return
    if _is_blocked_email(to_email):
        logger.info("Skipped email to blocked/test address: %s", to_email)
        return

    character_score = result.character_score or 0.0
    calling_score = result.calling_score or 0.0
    myimpact_score = result.myimpact_score or 0.0

    if myimpact_score >= 70:
        maturity_label, maturity_color = "Mature", "#0B6C80"
    elif myimpact_score >= 50:
        maturity_label, maturity_color = "Growing", "#F7A824"
    elif myimpact_score >= 30:
        maturity_label, maturity_color = "Developing", "#F7A824"
    else:
        maturity_label, maturity_color = "Beginning", "#E3A2A2"

    def _score_bar(score, max_val=10):
        pct = int((score / max_val) * 100) if score else 0
        if score >= 8:
            bar_color = "#0B6C80"
        elif score >= 5:
            bar_color = "#F7A824"
        else:
            bar_color = "#E3A2A2"
        return f"""
        <div style="flex:1; background:#f0f0f0; border-radius:4px; height:10px;">
          <div style="background:{bar_color}; border-radius:4px; height:10px; width:{pct}%;"></div>
        </div>"""

    def _trait_row(label, score):
        return f"""
        <div style="display:flex; align-items:center; gap:12px; padding:10px 0; border-top:1px solid #eee;">
          <span style="font-size:13px; color:#3F4644; min-width:220px;">{label}</span>
          {_score_bar(score)}
          <span style="font-size:13px; font-weight:bold; color:#0B6C80; min-width:36px; text-align:right;">{score}/10</span>
        </div>"""

    character_rows = "".join([
        _trait_row("Loving", result.c1_loving or 0),
        _trait_row("Joyful", result.c2_joyful or 0),
        _trait_row("Peaceful", result.c3_peaceful or 0),
        _trait_row("Patient", result.c4_patient or 0),
        _trait_row("Kind", result.c5_kind or 0),
        _trait_row("Good", result.c6_good or 0),
        _trait_row("Faithful", result.c7_faithful or 0),
        _trait_row("Gentle", result.c8_gentle or 0),
        _trait_row("Self-Controlled", result.c9_self_controlled or 0),
    ])

    calling_rows = "".join([
        _trait_row("I can name my top 3 Spiritual Gifts", result.cl1_know_gifts or 0),
        _trait_row("I know the people/causes God wants me to serve", result.cl2_know_people or 0),
        _trait_row("I am using my gifts to serve others", result.cl3_using_gifts or 0),
        _trait_row("I see God making a difference through me", result.cl4_see_impact or 0),
        _trait_row("I experience joy in serving others", result.cl5_experience_joy or 0),
        _trait_row("I regularly pray for people around me", result.cl6_pray_regularly or 0),
        _trait_row("I see people move toward faith", result.cl7_see_movement or 0),
        _trait_row("I receive support in my calling", result.cl8_receive_support or 0),
    ])

    cta_url = results_url or f"{settings.FRONTEND_URL}/dashboard"

    html = f"""
    <div style="font-family:Arial,sans-serif; max-width:620px; margin:0 auto; color:#3F4644;">
      <div style="background:#1a3a4a; padding:32px 24px; border-radius:8px 8px 0 0; text-align:center;">
        <h1 style="color:#ffffff; margin:0; font-size:24px;">Your MyImpact Results, {first_name}!</h1>
      </div>
      <div style="background:#f9f9f9; padding:24px; border-radius:0 0 8px 8px; border:1px solid #e0e0e0; border-top:none;">

        <!-- Score Hero -->
        <div style="background:#ffffff; border:1px solid #e0e0e0; border-radius:8px; padding:24px; text-align:center; margin-bottom:24px;">
          <p style="font-size:13px; color:#999; margin:0 0 8px; text-transform:uppercase; letter-spacing:1px;">Your MyImpact Score</p>
          <div style="display:flex; justify-content:center; align-items:center; gap:12px; flex-wrap:wrap;">
            <div>
              <p style="margin:0; font-size:13px; color:#0B6C80; font-weight:bold;">CHARACTER</p>
              <p style="margin:0; font-size:36px; font-weight:bold; color:#0B6C80;">{character_score:.1f}</p>
            </div>
            <span style="font-size:28px; color:#aaa;">&times;</span>
            <div>
              <p style="margin:0; font-size:13px; color:#F7A824; font-weight:bold;">CALLING</p>
              <p style="margin:0; font-size:36px; font-weight:bold; color:#F7A824;">{calling_score:.1f}</p>
            </div>
            <span style="font-size:28px; color:#aaa;">=</span>
            <div>
              <p style="margin:0; font-size:13px; color:#3F4644; font-weight:bold;">MYIMPACT</p>
              <p style="margin:0; font-size:36px; font-weight:bold; color:#3F4644;">{myimpact_score:.1f}</p>
            </div>
          </div>
          <div style="margin-top:16px;">
            <span style="background:{maturity_color}; color:#ffffff; border-radius:20px; padding:6px 20px;
                          font-size:14px; font-weight:bold;">{maturity_label}</span>
          </div>
          <p style="font-size:12px; color:#aaa; margin:12px 0 0;">Most first-time takers score between 4–25. The goal is steady growth, not perfection.</p>
        </div>

        <!-- Character -->
        <h2 style="color:#0B6C80; font-size:18px; margin:0 0 4px;">Character
          <span style="font-size:14px; font-weight:normal; color:#aaa; margin-left:8px;">Avg: {character_score:.1f}/10</span>
        </h2>
        <p style="font-size:13px; color:#666; margin:0 0 8px;">Fruit of the Spirit — Rate yourself as those who know you best would rate you.</p>
        {character_rows}

        <!-- Calling -->
        <h2 style="color:#F7A824; font-size:18px; margin:24px 0 4px;">Calling
          <span style="font-size:14px; font-weight:normal; color:#aaa; margin-left:8px;">Avg: {calling_score:.1f}/10</span>
        </h2>
        <p style="font-size:13px; color:#666; margin:0 0 8px;">Your Unique Design — Your Calling is the unique way God has designed you to partner with Him.</p>
        {calling_rows}

        <p style="text-align:center; margin:32px 0 0;">
          <a href="{cta_url}"
             style="background:#0B6C80; color:#ffffff; padding:14px 32px; text-decoration:none;
                    border-radius:6px; font-size:16px; font-weight:bold;">
            View Full Results
          </a>
        </p>
        <hr style="border:none; border-top:1px solid #eee; margin:32px 0;" />
        <p style="color:#999; font-size:12px; text-align:center;">
          Gift, Passion, Story Assessment Platform &mdash;
          <a href="{settings.FRONTEND_URL}" style="color:#999;">giftpassionstory.com</a>
        </p>
      </div>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": "Your MyImpact Assessment Results",
            "html": html,
        })
        logger.info("MyImpact result email sent to %s", to_email)
    except Exception as exc:
        logger.error("Failed to send MyImpact result email to %s: %s", to_email, exc)


def send_password_reset_email(to_email: str, reset_token: str) -> None:
    """Send a password reset email."""
    if not _get_client():
        return
    if _is_blocked_email(to_email):
        logger.info("Skipped email to blocked/test address: %s", to_email)
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


def send_primary_admin_welcome_email(to_email: str, church_name: str, reset_token: str) -> None:
    """Send a welcome email to a newly-created primary admin — includes a set-password link."""
    if not _get_client():
        return
    if _is_blocked_email(to_email):
        logger.info("Skipped email to blocked/test address: %s", to_email)
        return

    setup_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}&welcome=1"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #1a3a4a;">Welcome to GPS &mdash; {church_name}</h2>
      <p>A platform admin has set you up as the <strong>primary admin</strong> of
         <strong>{church_name}</strong> on the Gift, Passion, Story assessment platform.</p>
      <p>Click the button below to set your password and log in:</p>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{setup_url}"
           style="background-color: #1a3a4a; color: white; padding: 14px 28px;
                  text-decoration: none; border-radius: 6px; font-size: 16px;">
          Set Up My Account
        </a>
      </p>
      <p style="color: #666; font-size: 14px;">
        This link expires in 24 hours. If it expires, use &ldquo;Forgot password&rdquo;
        on the login page to request a new one.
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
            "subject": f"You're the primary admin of {church_name} on GPS",
            "html": html,
        })
        logger.info("Primary admin welcome email sent to %s", to_email)
    except Exception as exc:
        logger.error("Failed to send welcome email to %s: %s", to_email, exc)


def send_membership_approved_email(to_email: str, first_name: str, org_name: str) -> None:
    """Notify a user that their church membership request was approved."""
    if not _get_client():
        return
    if _is_blocked_email(to_email):
        logger.info("Skipped email to blocked/test address: %s", to_email)
        return

    dashboard_url = f"{settings.FRONTEND_URL}/dashboard"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #1a3a4a;">You're In! Welcome to {org_name}</h2>
      <p>Hi {first_name},</p>
      <p>Great news — <strong>{org_name}</strong> has approved your request to join.
         Your assessment results are now linked to the church.</p>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{dashboard_url}"
           style="background-color: #1a3a4a; color: white; padding: 14px 28px;
                  text-decoration: none; border-radius: 6px; font-size: 16px;">
          Go to Dashboard
        </a>
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
            "subject": f"You've been accepted into {org_name} on GPS",
            "html": html,
        })
        logger.info("Membership approved email sent to %s for org %s", to_email, org_name)
    except Exception as exc:
        logger.error("Failed to send membership approved email to %s: %s", to_email, exc)


def send_membership_declined_email(to_email: str, first_name: str, org_name: str) -> None:
    """Notify a user that their church membership request was declined."""
    if not _get_client():
        return
    if _is_blocked_email(to_email):
        logger.info("Skipped email to blocked/test address: %s", to_email)
        return

    account_url = f"{settings.FRONTEND_URL}/account"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #1a3a4a;">Membership Request Update</h2>
      <p>Hi {first_name},</p>
      <p>Unfortunately, your request to join <strong>{org_name}</strong> was not approved.
         If you believe this was a mistake, please reach out to your church directly.</p>
      <p>You can also search for a different church from your account page:</p>
      <p style="text-align: center; margin: 32px 0;">
        <a href="{account_url}"
           style="background-color: #1a3a4a; color: white; padding: 14px 28px;
                  text-decoration: none; border-radius: 6px; font-size: 16px;">
          Go to Account
        </a>
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
            "subject": "Update on your GPS church membership request",
            "html": html,
        })
        logger.info("Membership declined email sent to %s for org %s", to_email, org_name)
    except Exception as exc:
        logger.error("Failed to send membership declined email to %s: %s", to_email, exc)
