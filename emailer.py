"""
Email sender for the TCG Daily News Brief.

Supports two methods — the agent auto-detects which one to use based on
which environment variable you've set:

  METHOD 1 (recommended): Resend API — no 2FA required, just an API key
    → Set RESEND_API_KEY in your .env / GitHub secrets
    → Sign up free at https://resend.com (3,000 emails/month free)
    → Emails arrive FROM: TCG News Brief <onboarding@resend.dev>
      (or your own domain if you verify it in Resend)

  METHOD 2: Gmail SMTP — requires 2FA + App Password on the Gmail account
    → Set SMTP_USER, SMTP_PASSWORD in your .env / GitHub secrets
    → Only use this if the org Gmail account has 2FA enabled
"""

import os
import re
from datetime import datetime


# ─── Public Interface ─────────────────────────────────────────────────────────

def send_brief_email(
    recipients: list[str],
    subject: str,
    body_text: str,
    body_html: str | None = None,
):
    """
    Send the daily brief. Auto-detects Resend vs. SMTP based on env vars.
    Prefers Resend if RESEND_API_KEY is set.
    """
    if not body_html:
        body_html = plain_to_html(body_text)

    if os.environ.get("RESEND_API_KEY"):
        _send_via_resend(recipients, subject, body_text, body_html)
    elif os.environ.get("SMTP_PASSWORD"):
        _send_via_smtp(recipients, subject, body_text, body_html)
    else:
        raise EnvironmentError(
            "No email credentials found.\n"
            "Option 1 (easiest): Set RESEND_API_KEY — get a free key at https://resend.com\n"
            "Option 2: Set SMTP_USER + SMTP_PASSWORD (requires Gmail 2FA + App Password)"
        )


# ─── Resend (recommended) ─────────────────────────────────────────────────────

def _send_via_resend(recipients, subject, body_text, body_html):
    """Send via Resend API — no 2FA needed, just a free API key."""
    try:
        import resend
    except ImportError:
        raise ImportError(
            "Install the resend package: pip install resend\n"
            "(It's already in requirements.txt — run: pip install -r requirements.txt)"
        )

    resend.api_key = os.environ["RESEND_API_KEY"]

    # FROM address: use verified domain if set, otherwise Resend's free sandbox sender
    from_address = os.environ.get(
        "RESEND_FROM",
        "TCG News Brief <onboarding@resend.dev>"
    )

    params = {
        "from":    from_address,
        "to":      recipients,
        "subject": subject,
        "text":    body_text,
        "html":    body_html,
    }

    resend.Emails.send(params)
    print(f"✅ Email sent via Resend to {', '.join(recipients)}")


# ─── Gmail SMTP (fallback) ────────────────────────────────────────────────────

def _send_via_smtp(recipients, subject, body_text, body_html):
    """Send via Gmail SMTP — requires 2FA + App Password on the Gmail account."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_user   = os.environ.get("SMTP_USER")
    smtp_pass   = os.environ.get("SMTP_PASSWORD")
    from_name   = os.environ.get("SMTP_FROM_NAME", "TCG News Brief")
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port   = int(os.environ.get("SMTP_PORT", "587"))

    if not smtp_user or not smtp_pass:
        raise EnvironmentError("SMTP_USER and SMTP_PASSWORD must both be set.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{from_name} <{smtp_user}>"
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html",  "utf-8"))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, recipients, msg.as_string())

    print(f"✅ Email sent via SMTP to {', '.join(recipients)}")


# ─── HTML Formatter ───────────────────────────────────────────────────────────

def plain_to_html(text: str) -> str:
    """Convert plain text brief to a polished newsletter-style HTML email."""
    date_str = datetime.now().strftime("%B %-d, %Y")
    lines = text.split("\n")

    body_rows = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        elif "THE COMMON GOOD" in s or "DAILY NEWS BRIEF" in s:
            continue  # handled in header
        elif s.startswith("Generated") or "=" * 10 in s:
            continue  # skip these
        elif s.startswith("━━━"):
            title = s.replace("━", "").strip()
            body_rows.append(
                f'<tr><td style="padding:18px 0 6px;">'
                f'<div style="background:#1a1a2e;color:white;padding:7px 16px;'
                f'font-family:Arial,sans-serif;font-weight:700;font-size:11px;'
                f'letter-spacing:2px;border-radius:3px;">{title}</div>'
                f'</td></tr>'
            )
        elif s.startswith("[ ") and s.endswith(" ]"):
            title = s[2:-2].strip()
            body_rows.append(
                f'<tr><td style="padding:12px 0 4px;">'
                f'<div style="font-family:Arial,sans-serif;font-weight:700;'
                f'font-size:10px;letter-spacing:1.5px;color:#1a1a2e;'
                f'border-bottom:2px solid #1a1a2e;padding-bottom:4px;">{title}</div>'
                f'</td></tr>'
            )
        elif s.startswith("•"):
            content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s[1:].strip())
            body_rows.append(
                f'<tr><td style="padding:6px 0 2px 0;">'
                f'<div style="font-family:Arial,sans-serif;font-size:13px;'
                f'line-height:1.65;color:#1a1a1a;padding-left:12px;'
                f'border-left:3px solid #1a1a2e;">{content}</div>'
                f'</td></tr>'
            )
        elif s.startswith("http"):
            body_rows.append(
                f'<tr><td style="padding:2px 0 1px 15px;">'
                f'<a href="{s}" style="font-family:Arial,sans-serif;font-size:11px;'
                f'color:#0066cc;text-decoration:none;">🔗 Read full article</a>'
                f'</td></tr>'
            )
        elif s.startswith("(") and ")" in s:
            body_rows.append(
                f'<tr><td style="padding:1px 0 10px 15px;">'
                f'<span style="font-family:Arial,sans-serif;font-size:10px;'
                f'color:#888;">{s}</span></td></tr>'
            )

    rows_html = "\n".join(body_rows)

    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f4f4f4;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:20px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="background:white;border-radius:6px;overflow:hidden;">

  <!-- Header -->
  <tr><td style="background:#1a1a2e;padding:24px 32px;">
    <div style="font-family:Arial,sans-serif;font-size:11px;color:#aab;letter-spacing:2px;margin-bottom:4px;">THE COMMON GOOD</div>
    <div style="font-family:Arial,sans-serif;font-size:22px;font-weight:700;color:white;">Daily News Brief</div>
    <div style="font-family:Arial,sans-serif;font-size:11px;color:#aab;margin-top:4px;">{date_str}</div>
  </td></tr>

  <!-- Body -->
  <tr><td style="padding:16px 32px 32px;">
    <table width="100%" cellpadding="0" cellspacing="0">
      {rows_html}
    </table>
  </td></tr>

  <!-- Footer -->
  <tr><td style="background:#f8f8f8;padding:14px 32px;border-top:1px solid #eee;">
    <p style="font-family:Arial,sans-serif;font-size:10px;color:#999;margin:0;">
      Generated by TCG News Brief Agent · For internal use only · Review before publishing
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    send_brief_email(
        recipients=["test@example.com"],
        subject="TCG Brief Test",
        body_text="Test email from TCG News Brief agent.",
    )
