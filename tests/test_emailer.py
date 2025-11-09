from __future__ import annotations

import pytest

from src import emailer


def test_send_email_failure_triggers_system_exit(monkeypatch):
    env = {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "user@example.com",
        "SMTP_PASS": "pass",
        "SMTP_FROM": "bot@example.com",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    class BrokenSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self, *args, **kwargs):
            return None

        def login(self, *args, **kwargs):
            return None

        def send_message(self, *args, **kwargs):
            raise RuntimeError("SMTP failure")

    monkeypatch.setattr(emailer.smtplib, "SMTP", BrokenSMTP)

    with pytest.raises(SystemExit):
        emailer.send_email({}, "dest@example.com", "Subject", "Body")
