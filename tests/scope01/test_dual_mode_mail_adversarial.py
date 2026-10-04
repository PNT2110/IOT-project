# tests/scope01/test_dual_mode_mail_adversarial.py
import asyncio
import gc
import inspect
import smtplib
import socket
import time
import warnings
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from server.app.mail import DualModeMailCall, SmtpEmailSender


def test_dual_mode_unawaited_warning_suppression():
    """Verify that calling send_code without await generates NO RuntimeWarning."""
    sender = SmtpEmailSender(
        host="smtp.fake.local",
        port=587,
        username="user",
        password="password",
        sender="noreply@fake.local",
    )

    with patch.object(sender, "_send_blocking", return_value=None):
        with warnings.catch_warnings(record=True) as recorded_warnings:
            warnings.simplefilter("always")
            # Invoke synchronously without await
            call = sender.send_code("user@example.com", "LOGIN", "123456", datetime.now(timezone.utc))
            assert isinstance(call, DualModeMailCall)
            # Delete and force garbage collection
            del call
            gc.collect()

            coro_warnings = [
                w for w in recorded_warnings
                if issubclass(w.category, RuntimeWarning) and "coroutine" in str(w.message).lower()
            ]
            assert len(coro_warnings) == 0, f"Unexpected coroutine warnings: {coro_warnings}"


@pytest.mark.anyio
async def test_dual_mode_concurrency_and_loop_non_blocking_high_load():
    """Verify that 200 concurrent email sends do not block the asyncio event loop."""
    sender = SmtpEmailSender(
        host="smtp.fake.local",
        port=587,
        username="user",
        password="password",
        sender="noreply@fake.local",
    )

    # Simulate 30ms blocking network delay per SMTP transaction
    def mock_send(recipient, purpose, code, sent_at):
        time.sleep(0.03)

    heartbeat_count = 0
    max_jitter_ms = 0.0
    stop_event = asyncio.Event()

    async def heartbeat():
        nonlocal heartbeat_count, max_jitter_ms
        prev = asyncio.get_running_loop().time()
        while not stop_event.is_set():
            await asyncio.sleep(0.005)  # 5ms interval
            now = asyncio.get_running_loop().time()
            jitter = abs((now - prev) * 1000.0 - 5.0)
            if jitter > max_jitter_ms:
                max_jitter_ms = jitter
            prev = now
            heartbeat_count += 1

    with patch.object(sender, "_send_blocking", side_effect=mock_send):
        hb_task = asyncio.create_task(heartbeat())
        now = datetime.now(timezone.utc)

        start = time.perf_counter()
        tasks = [
            sender.send_code(f"batch_{i}@test.com", "OTP", f"{100000+i}", now)
            for i in range(200)
        ]
        await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        stop_event.set()
        await hb_task

    # 200 tasks * 30ms sequential would take 6.0 seconds.
    # Concurrently with max_workers=20, it should complete in ~0.3 - 0.7s.
    assert elapsed < 3.0, f"High load took too long: {elapsed:.2f}s"
    assert heartbeat_count >= 20, f"Event loop was starved! Only {heartbeat_count} ticks"
    assert max_jitter_ms < 50.0, f"High loop jitter: {max_jitter_ms:.2f}ms"


@pytest.mark.anyio
@pytest.mark.parametrize("exc_type,exc_val", [
    (socket.timeout, socket.timeout("timed out")),
    (smtplib.SMTPServerDisconnected, smtplib.SMTPServerDisconnected("unexpected disconnect")),
    (smtplib.SMTPConnectError, smtplib.SMTPConnectError(421, "Service unavailable")),
    (smtplib.SMTPAuthenticationError, smtplib.SMTPAuthenticationError(535, "Authentication failed")),
    (smtplib.SMTPRecipientsRefused, smtplib.SMTPRecipientsRefused({"bad@test.com": (550, "User unknown")})),
    (ConnectionRefusedError, ConnectionRefusedError("Connection refused")),
])
async def test_dual_mode_exception_propagation(exc_type, exc_val):
    """Verify that all SMTP and network exceptions propagate correctly through DualModeMailCall."""
    sender = SmtpEmailSender(
        host="smtp.fake.local",
        port=587,
        username="user",
        password="password",
        sender="noreply@fake.local",
    )

    with patch.object(sender, "_send_blocking", side_effect=exc_val):
        with pytest.raises(exc_type):
            await sender.send_code("user@test.com", "LOGIN", "123456", datetime.now(timezone.utc))


@pytest.mark.anyio
async def test_dual_mode_cancellation_safety():
    """Verify that cancellation of awaited DualModeMailCall raises CancelledError and cleans up."""
    sender = SmtpEmailSender(
        host="smtp.fake.local",
        port=587,
        username="user",
        password="password",
        sender="noreply@fake.local",
    )

    def slow_send(*args, **kwargs):
        time.sleep(1.0)

    with patch.object(sender, "_send_blocking", side_effect=slow_send):
        task = asyncio.create_task(sender.send_code("dest@example.com", "LOGIN", "123456", datetime.now(timezone.utc)))
        await asyncio.sleep(0.02)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task
