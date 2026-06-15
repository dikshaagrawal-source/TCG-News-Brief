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
    """Convert plain text brief to a styled HTML email."""
    lines = text.split("\n")
    html = [
        '<html><body style="font-family:Arial,sans-serif;max-width:700px;'
        'margin:auto;padding:20px;color:#1a1a1a;">',
        f'<p style="color:#6c757d;font-size:0.85em;">Generated '
        f'{datetime.now().strftime("%B %-d, %Y")}</p>',
        '<hr style="border:1px solid #dee2e6;">',
    ]

    for line in lines:
        s = line.strip()
        if not s:
            html.append("<br>")
        elif s.startswith("━━━"):
            title = s.replace("━", "").strip()
            html.append(
                f'<div style="background:#1a1a2e;color:white;padding:5px 12px;'
                f'border-radius:3px;font-weight:700;font-size:0.8em;'
                f'letter-spacing:1.5px;margin:16px 0 6px;">{title}</div>'
            )
        elif s.startswith("[ ") and s.endswith(" ]"):
            title = s[2:-2].strip()
            html.append(
                f'<div style="font-weight:700;font-size:0.78em;letter-spacing:1px;'
                f'border-bottom:2px solid #1a1a2e;padding-bottom:2px;margin:10px 0 4px;">'
                f'{title}</div>'
            )
        elif s.startswith("•"):
            content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s[1:].strip())
            html.append(
                f'<p style="margin:6px 0;padding-left:10px;border-left:3px solid #1a1a2e;'
                f'font-size:0.88em;line-height:1.6;">{content}</p>'
            )
        elif s.startswith("http"):
            html.append(
                f'<p style="margin:2px 0 2px 13px;font-size:0.78em;">'
                f'<a href="{s}" style="color:#0066cc;">🔗 Read article</a></p>'
            )
        elif s.startswith("(") and ")" in s:
            html.append(
                f'<p style="margin:0 0 8px 13px;color:#6c757d;font-size:0.75em;">{s}</p>'
            )
        elif s.startswith("THE COMMON GOOD"):
            html.append(f'<h2 style="color:#1a1a2e;margin-bottom:2px;">{s}</h2>')
        elif "=" * 10 in s:
            html.append('<hr style="border:1px solid #dee2e6;margin:8px 0;">')
        else:
            html.append(f'<p style="font-size:0.85em;color:#6c757d;">{s}</p>')

    html.append("</body></html>")
    return "\n".join(html)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    send_brief_email(
        recipients=["test@example.com"],
        subject="TCG Brief Test",
        body_text="Test email from TCG News Brief agent.",
    )
