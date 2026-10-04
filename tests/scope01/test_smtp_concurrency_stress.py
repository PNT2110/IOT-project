# tests/scope01/test_smtp_concurrency_stress.py
from __future__ import annotations

import asyncio
import inspect
import smtplib
import socket
import threading
import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from server.app.mail import SmtpEmailSender


@pytest.mark.anyio
async def test_event_loop_responsiveness_under_heavy_smtp_load():
    """Verify that 50 concurrent SMTP sends do NOT starve the asyncio event loop."""
    sender = SmtpEmailSender(
        host="smtp.stress-test.local",
        port=587,
        username="stress@test.local",
        password="secret",
        sender="noreply@test.local",
    )

    # Mock blocking SMTP with a realistic network delay (50ms)
    def mock_send(recipient, purpose, code, sent_at):
        time.sleep(0.05)

    heartbeat_ticks = 0
    max_heartbeat_jitter_ms = 0.0
    stop_heartbeat = asyncio.Event()

    async def heartbeat():
        nonlocal heartbeat_ticks, max_heartbeat_jitter_ms
        prev = asyncio.get_running_loop().time()
        while not stop_heartbeat.is_set():
            await asyncio.sleep(0.005)  # 5ms tick
            now = asyncio.get_running_loop().time()
            elapsed_ms = (now - prev) * 1000.0
            jitter = abs(elapsed_ms - 5.0)
            if jitter > max_heartbeat_jitter_ms:
                max_heartbeat_jitter_ms = jitter
            prev = now
            heartbeat_ticks += 1

    with patch.object(sender, "_send_blocking", side_effect=mock_send):
        heartbeat_task = asyncio.create_task(heartbeat())
        now = datetime.now(timezone.utc)

        start_time = time.monotonic()
        # Launch 50 concurrent email dispatches
        tasks = [
            sender.send_code(f"user_{i}@example.com", "LOGIN_OTP", f"10000{i}", now)
            for i in range(50)
        ]
        await asyncio.gather(*tasks)
        total_time = time.monotonic() - start_time

        stop_heartbeat.set()
        await heartbeat_task

    # 1. Total time for 50 requests (each 50ms): in a blocking loop, this would take at least 2.5s.
    # Concurrently via threadpool, it must finish much faster (< 1.5s).
    assert total_time < 1.5, f"Expected concurrent execution < 1.5s, took {total_time:.2f}s"

    # 2. Heartbeat must have ticked repeatedly while emails were being sent
    assert heartbeat_ticks > 10, f"Event loop was starved! Heartbeat ticks: {heartbeat_ticks}"

    # 3. Heartbeat jitter must remain low (< 50ms). If loop blocked, jitter would exceed 50ms+.
    assert max_heartbeat_jitter_ms < 50.0, f"Excessive jitter: {max_heartbeat_jitter_ms:.2f}ms"


@pytest.mark.anyio
async def test_high_concurrency_throughput():
    """Stress test 100 concurrent email sends."""
    sender = SmtpEmailSender(
        host="smtp.stress-test.local",
        port=587,
        username="stress@test.local",
        password="secret",
        sender="noreply@test.local",
    )

    send_count = 0
    lock = threading.Lock()

    def mock_send(recipient, purpose, code, sent_at):
        nonlocal send_count
        time.sleep(0.01)
        with lock:
            send_count += 1

    with patch.object(sender, "_send_blocking", side_effect=mock_send):
        now = datetime.now(timezone.utc)
        tasks = [
            sender.send_code(f"batch_{i}@example.com", "ALERT", "999999", now)
            for i in range(100)
        ]
        await asyncio.gather(*tasks)

    assert send_count == 100


@pytest.mark.anyio
async def test_smtp_error_propagation_in_async_context():
    """Verify that SMTP exceptions are raised cleanly in the coroutine."""
    sender = SmtpEmailSender(
        host="127.0.0.1",
        port=1,  # Non-existent port
        username=None,
        password=None,
        sender="noreply@example.com",
    )

    now = datetime.now(timezone.utc)
    # Connecting to port 1 must raise an exception (ConnectionRefused or OSError)
    with pytest.raises((OSError, smtplib.SMTPConnectError)):
        await sender.send_code("fail@example.com", "TEST", "000000", now)


def test_smtp_sender_sync_fallback():
    """Verify send_code_sync executes synchronously without needing an event loop."""
    sender = SmtpEmailSender(
        host="smtp.test.local",
        port=25,
        username=None,
        password=None,
        sender="noreply@test.local",
    )

    executed = False
    def mock_send(recipient, purpose, code, sent_at):
        nonlocal executed
        executed = True

    with patch.object(sender, "_send_blocking", side_effect=mock_send):
        sender.send_code_sync("sync@example.com", "TEST", "123456", datetime.now(timezone.utc))

    assert executed is True
