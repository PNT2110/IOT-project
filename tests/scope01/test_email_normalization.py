from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import inspect
from unittest.mock import patch, MagicMock

import pytest

from server.app.mail import SmtpEmailSender
from server.app.security import normalize_email


def test_gmail_dot_stripping():
    assert normalize_email("john.doe@gmail.com") == "johndoe@gmail.com"
    assert normalize_email("j.o.h.n.d.o.e@gmail.com") == "johndoe@gmail.com"
    assert normalize_email("johndoe@gmail.com") == "johndoe@gmail.com"


def test_gmail_subaddress_tag_stripping():
    assert normalize_email("johndoe+test@gmail.com") == "johndoe@gmail.com"
    assert normalize_email("johndoe+newsletter123@gmail.com") == "johndoe@gmail.com"
    assert normalize_email("johndoe+tag1+tag2@gmail.com") == "johndoe@gmail.com"


def test_gmail_combined_dots_and_subaddress():
    # Primary requirement from ORIGINAL_REQUEST.md
    assert normalize_email("john.doe+test@gmail.com") == "johndoe@gmail.com"
    assert normalize_email("John.Doe+Test@gmail.com") == "johndoe@gmail.com"
    assert normalize_email("  john.doe+test@gmail.com  ") == "johndoe@gmail.com"


def test_googlemail_canonicalization():
    assert normalize_email("john.doe+test@googlemail.com") == "johndoe@gmail.com"
    assert normalize_email("John.Doe@googlemail.com") == "johndoe@gmail.com"
    assert normalize_email("johndoe@googlemail.com") == "johndoe@gmail.com"


def test_aliased_emails_normalize_identically():
    base = normalize_email("johndoe@gmail.com")
    assert normalize_email("john.doe@gmail.com") == base
    assert normalize_email("j.o.h.n.doe@gmail.com") == base
    assert normalize_email("john.doe+promo@gmail.com") == base
    assert normalize_email("John.Doe+Work@googlemail.com") == base


def test_non_gmail_domains_preserve_dots_and_strip_subaddress():
    # Non-Gmail domains preserve dots in local part but strip +tag subaddress
    assert normalize_email("john.doe+test@example.com") == "john.doe@example.com"
    assert normalize_email("pilot.lead@domain.org") == "pilot.lead@domain.org"
    assert normalize_email("Operator.Admin+Alerts@dronecorp.vn") == "operator.admin@dronecorp.vn"


def test_identifiers_without_at_symbol():
    # Login identifier can be a plain username
    assert normalize_email("admin") == "admin"
    assert normalize_email("  OPERATOR_1  ") == "operator_1"
    assert normalize_email("system_user") == "system_user"


@pytest.mark.anyio
async def test_smtp_email_sender_is_non_blocking_coroutine():
    sender = SmtpEmailSender(
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        password="secretpassword",
        sender="noreply@example.com",
    )
    # Verify send_code is natively a coroutine function
    assert inspect.iscoroutinefunction(sender.send_code)

    # Verify that calling send_code wraps execution and does not block
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_instance = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_instance

        sent_time = datetime.now(timezone.utc)
        await sender.send_code("recipient@example.com", "LOGIN_CHALLENGE", "123456", sent_time)

        mock_smtp_cls.assert_called_once_with("smtp.example.com", 587, timeout=15)
        mock_instance.starttls.assert_called_once()
        mock_instance.login.assert_called_once_with("user@example.com", "secretpassword")
        mock_instance.send_message.assert_called_once()


def test_smtp_email_sender_synchronous_caller_safety():
    """Verify that synchronous callers (such as services.py create_email_code) can call send_code without await or warnings."""
    import time
    import warnings

    sender = SmtpEmailSender(
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        password="secretpassword",
        sender="noreply@example.com",
    )
    sent_calls = []

    def mock_send(recipient, purpose, code, sent_at):
        sent_calls.append((recipient, purpose, code))

    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        with patch.object(sender, "_send_blocking", side_effect=mock_send):
            sent_time = datetime.now(timezone.utc)
            result = sender.send_code("sync_user@example.com", "REGISTER", "654321", sent_time)
            time.sleep(0.1)
            del result

        coro_warnings = [w for w in captured_warnings if issubclass(w.category, RuntimeWarning)]
        assert len(coro_warnings) == 0
        assert len(sent_calls) == 1
        assert sent_calls[0] == ("sync_user@example.com", "REGISTER", "654321")
