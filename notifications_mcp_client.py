# notifications_mcp_client.py

import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional


def _get_env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def send_hitl_email(
    claim_id: str,
    to_email: Optional[str],
    decision: str,
    fraud_score: float,
    risk_bucket: str,
    notes: str,
    evidence_summary: Optional[str] = None,
) -> None:
    """
    Very simple email sender for HITL escalation.
    This is your 'MCP-like' external side-effect.

    Configure via env vars:

      EMAIL_SMTP_HOST       (e.g. "smtp.gmail.com")
      EMAIL_SMTP_PORT       (e.g. "587")
      EMAIL_SMTP_USER       (username or email)
      EMAIL_SMTP_PASSWORD   (app password)
      EMAIL_FROM            (from address)
      EMAIL_HITL_TO         (default recipient if to_email is None)
    """

    smtp_host = _get_env("EMAIL_SMTP_HOST")
    smtp_port = int(_get_env("EMAIL_SMTP_PORT", "587"))
    smtp_user = _get_env("EMAIL_SMTP_USER")
    smtp_password = _get_env("EMAIL_SMTP_PASSWORD")
    email_from = _get_env("EMAIL_FROM")
    default_to = _get_env("EMAIL_HITL_TO")

    recipient = to_email or default_to

    subject = f"[HITL] Review needed for claim {claim_id}"

    body_lines = [
        f"Claim ID: {claim_id}",
        f"Decision: {decision}",
        f"Fraud score: {fraud_score}",
        f"Risk bucket: {risk_bucket}",
        "",
        "Notes:",
        notes or "(none)",
    ]

    if evidence_summary:
        body_lines.extend(
            [
                "",
                "Evidence summary:",
                evidence_summary,
            ]
        )

    body = "\n".join(body_lines)

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = recipient

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
