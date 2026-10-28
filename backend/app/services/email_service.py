import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings

logger = logging.getLogger("tursathi.email")


def send_otp_email(recipient_email: str, recipient_name: str, otp_code: str) -> bool:
    """
    Sends a 6-digit OTP email for password recovery via SMTP.
    Uses TLS on port 587 (or configured SMTP port).

    In development mode, if SMTP credentials are not configured, safely
    permits local dev testing without crashing. In production mode, requires
    valid SMTP credentials.
    """
    smtp_host = (settings.SMTP_HOST or "").strip()
    smtp_user = (settings.SMTP_USER or "").strip()
    smtp_pass = (settings.SMTP_PASSWORD or "").strip()
    from_email = (settings.SMTP_FROM_EMAIL or smtp_user or "noreply@tursathi.ai").strip()
    from_name = settings.SMTP_FROM_NAME or "TurSathi AI"

    # Dev fallback when SMTP credentials are not configured
    if not smtp_host or not smtp_user or not smtp_pass:
        if settings.ENVIRONMENT == "development":
            logger.info(
                "[DEV ONLY] SMTP not configured. Development OTP generated for %s",
                recipient_email
            )
            return True
        logger.error("[SMTP ERROR] SMTP credentials are not configured on the production server.")
        return False

    display_name = recipient_name.strip() if recipient_name and recipient_name.strip() else "Farmer"

    subject = f"{otp_code} is your TurSathi AI password reset code"

    text_body = f"""Hello {display_name},

We received a request to reset your password for your TurSathi AI account.

Your 6-digit verification code is:
{otp_code}

This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.

SECURITY NOTICE:
- Do not share this code with anyone. TurSathi AI representatives will never ask for your code.
- If you did not request this password reset, you can safely ignore this email. Your account remains secure.

Sincerely,
The TurSathi AI Team
Smart Crop Care & Disease Guidance
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>TurSathi AI Password Reset</title>
</head>
<body style="margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F7F5ED; color: #1D3328;">
  <div style="max-width: 520px; margin: 0 auto; background-color: #FFFFFF; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 16px rgba(16, 59, 45, 0.08); border: 1px solid #E3E7DE;">
    <!-- Header -->
    <div style="background-color: #103B2D; padding: 28px 24px; text-align: center;">
      <h1 style="margin: 0; color: #F6F1E5; font-size: 26px; font-weight: 700; letter-spacing: 0.5px;">
        <span style="color: #F6F1E5;">Tur</span><span style="color: #D8BD79;">Sathi</span> <span style="color: #F6F1E5; font-weight: 400; font-size: 20px;">AI</span>
      </h1>
      <p style="margin: 6px 0 0; color: #D3DDCF; font-size: 13px;">Tur Leaf Disease Detection &amp; Smart Spray Guidance</p>
    </div>

    <!-- Body -->
    <div style="padding: 32px 24px;">
      <h2 style="margin: 0 0 12px; color: #1D3328; font-size: 20px; font-weight: 700;">Password Reset Verification</h2>
      <p style="margin: 0 0 20px; color: #526458; font-size: 14px; line-height: 1.5;">
        Hello <strong>{display_name}</strong>, we received a request to reset your password. Use the verification code below to proceed:
      </p>

      <!-- Code Box -->
      <div style="margin: 24px 0; padding: 18px; background-color: #F2F8F4; border: 2px dashed #267451; border-radius: 12px; text-align: center;">
        <span style="font-family: 'Courier New', Courier, monospace; font-size: 34px; font-weight: 700; letter-spacing: 8px; color: #145236;">
          {otp_code}
        </span>
        <div style="margin-top: 8px; color: #55745F; font-size: 12px; font-weight: 600;">
          Expires in {settings.OTP_EXPIRE_MINUTES} minutes
        </div>
      </div>

      <!-- Security Notice -->
      <div style="margin-top: 24px; padding: 14px 16px; background-color: #FDF9EE; border-left: 4px solid #C5A45C; border-radius: 4px;">
        <p style="margin: 0; color: #735A1E; font-size: 12px; line-height: 1.5;">
          <strong>Security Notice:</strong> Never share this code with anyone. If you did not request a password reset, please ignore this email. Your password will not change.
        </p>
      </div>
    </div>

    <!-- Footer -->
    <div style="background-color: #F7F5ED; padding: 18px 24px; border-top: 1px solid #E8ECE3; text-align: center;">
      <p style="margin: 0; color: #879589; font-size: 12px;">
        &copy; 2026 TurSathi AI. Dedicated to healthier crops and prosperous farmers.
      </p>
    </div>
  </div>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = recipient_email

    part1 = MIMEText(text_body, "plain", "utf-8")
    part2 = MIMEText(html_body, "html", "utf-8")
    msg.attach(part1)
    msg.attach(part2)

    try:
        if settings.SMTP_TLS:
            server = smtplib.SMTP(smtp_host, settings.SMTP_PORT, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP(smtp_host, settings.SMTP_PORT, timeout=10)

        server.login(smtp_user, smtp_pass)
        server.sendmail(from_email, [recipient_email], msg.as_string())
        server.quit()
        logger.info("[SMTP SUCCESS] Password reset OTP sent successfully to %s", recipient_email)
        return True
    except Exception as exc:
        logger.error("[SMTP ERROR] Failed to send password reset email to %s: %s", recipient_email, str(exc))
        return False
