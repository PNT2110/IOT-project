from __future__ import annotations

import asyncio
import collections.abc
import concurrent.futures
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
import inspect
import json
from pathlib import Path
import smtplib
from typing import Any


@dataclass(frozen=True)
class FakeMail:
    recipient: str
    purpose: str
    code: str
    sent_at: datetime


class FakeEmailSender:
    """In-memory dev/test sink; never enabled as a real email provider."""

    def __init__(self, outbox_path: str | None = None) -> None:
        self.messages: list[FakeMail] = []
        self.outbox_path = Path(outbox_path) if outbox_path else None

    def send_code(self, recipient: str, purpose: str, code: str, sent_at: datetime) -> None:
        self.messages.append(FakeMail(recipient, purpose, code, sent_at))
        if self.outbox_path:
            self.outbox_path.parent.mkdir(parents=True, exist_ok=True)
            with self.outbox_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"recipient": recipient, "purpose": purpose, "code": code, "sent_at": sent_at.isoformat()}) + "\n")

    def latest(self, recipient: str | None = None, purpose: str | None = None) -> FakeMail | None:
        for message in reversed(self.messages):
            if recipient and message.recipient != recipient:
                continue
            if purpose and message.purpose != purpose:
                continue
            return message
        return None


class UnconfiguredEmailSender:
    """Explicit production failure until an operator configures SMTP."""

    def send_code(self, recipient: str, purpose: str, code: str, sent_at: datetime) -> None:
        raise RuntimeError("SMTP email delivery is not configured")


class DualModeMailCall(collections.abc.Coroutine):
    """Coroutine wrapper executing via threadpool, safe for async and sync callers alike."""

    def __init__(self, future: concurrent.futures.Future[None]) -> None:
        self._future = future
        self._iter: Any = None

    def _get_iter(self) -> Any:
        if self._iter is None:
            self._iter = asyncio.wrap_future(self._future).__await__()
        return self._iter

    def send(self, val: Any) -> Any:
        return self._get_iter().send(val)

    def throw(self, *args: Any) -> Any:
        return self._get_iter().throw(*args)

    def close(self) -> None:
        if self._iter is not None and hasattr(self._iter, "close"):
            self._iter.close()

    def __await__(self) -> Any:
        return self._get_iter()


class SmtpEmailSender:
    """Non-blocking SMTP adapter for short OTP messages."""

    def __init__(self, host: str, port: int, username: str | None, password: str | None, sender: str) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = sender
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=20, thread_name_prefix="smtp_sender")

    def _send_blocking(self, recipient: str, purpose: str, code: str, sent_at: datetime) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = recipient
        message["Subject"] = "Drone Zone Check - mã xác nhận"
        message.set_content(
            f"Mã xác nhận Drone Zone Check của bạn là {code}.\n"
            f"Mã hết hạn sau ít phút và chỉ dùng một lần. Nếu bạn không yêu cầu mã này, hãy bỏ qua thư."
        )
        with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
            smtp.starttls()
            if self.username:
                smtp.login(self.username, self.password or "")
            smtp.send_message(message)

    def send_code(self, recipient: str, purpose: str, code: str, sent_at: datetime) -> Any:
        fut = self._executor.submit(self._send_blocking, recipient, purpose, code, sent_at)
        return DualModeMailCall(fut)

    def send_code_sync(self, recipient: str, purpose: str, code: str, sent_at: datetime) -> None:
        self._send_blocking(recipient, purpose, code, sent_at)


inspect.markcoroutinefunction(SmtpEmailSender.send_code)


def email_sender_for_settings(settings: Any):
    """Select the explicit mail adapter for an app or local bootstrap command."""
    if settings.app_env in {"development", "test"}:
        return FakeEmailSender(settings.fake_mail_outbox)
    if settings.smtp_host and settings.smtp_from:
        return SmtpEmailSender(settings.smtp_host, settings.smtp_port, settings.smtp_username, settings.smtp_password, settings.smtp_from)
    return UnconfiguredEmailSender()
