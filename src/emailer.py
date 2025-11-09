from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any, Dict

logger = logging.getLogger(__name__)
SMTP_ENV_VARS = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "SMTP_FROM")


def send_email(smtp_conf: Dict[str, Any], to_addr: str, subject: str, body: str) -> None:
    """Send a plaintext email via SMTP using credentials from environment variables."""
    settings = _load_smtp_settings()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings["from_addr"]
    message["To"] = to_addr
    message.set_content(body, subtype="plain", charset="utf-8")

    timeout = float(smtp_conf.get("timeout", 30))
    use_ssl = bool(smtp_conf.get("use_ssl", False))
    use_starttls = bool(smtp_conf.get("use_starttls", not use_ssl))

    try:
        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                settings["host"], settings["port"], timeout=timeout, context=context
            ) as smtp:
                _auth_and_send(smtp, settings, message)
        else:
            with smtplib.SMTP(settings["host"], settings["port"], timeout=timeout) as smtp:
                if use_starttls:
                    context = ssl.create_default_context()
                    smtp.starttls(context=context)
                _auth_and_send(smtp, settings, message)
    except Exception as exc:  # pragma: no cover - smtplib errors depend on environment
        logger.error("Failed to send email via SMTP: %s", exc)
        raise SystemExit(1) from exc


def _auth_and_send(smtp: smtplib.SMTP, settings: Dict[str, Any], message: EmailMessage) -> None:
    if settings["username"] and settings["password"]:
        smtp.login(settings["username"], settings["password"])
    smtp.send_message(message)


def _load_smtp_settings() -> Dict[str, Any]:
    missing = [var for var in SMTP_ENV_VARS if not os.getenv(var)]
    if missing:
        message = f"Missing required SMTP environment variables: {', '.join(missing)}"
        logger.error(message)
        raise SystemExit(message)

    host = os.environ["SMTP_HOST"]
    port_raw = os.environ["SMTP_PORT"]
    try:
        port = int(port_raw)
    except ValueError as exc:
        message = f"SMTP_PORT must be an integer, got {port_raw}"
        logger.error(message)
        raise SystemExit(message) from exc

    return {
        "host": host,
        "port": port,
        "username": os.environ["SMTP_USER"],
        "password": os.environ["SMTP_PASS"],
        "from_addr": os.environ["SMTP_FROM"],
    }
