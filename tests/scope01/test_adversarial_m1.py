from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import inspect
import smtplib
import socket
import time
from unittest.mock import MagicMock, patch

import pytest

from server.app.mail import SmtpEmailSender
from server.app.security import normalize_email


# ============================================================================
# PROBE 2: Adversarial Email Normalization Testing
# ============================================================================

def test_adversarial_gmail_variations():
    # Valid canonical forms must match
    assert normalize_email("John.Doe@GMAIL.COM") == "johndoe@gmail.com"
    assert normalize_email("  john.doe+work+urgent@googlemail.com  ") == "johndoe@gmail.com"
    assert normalize_email("j.o.h.n...d.o.e+tag@gmail.com") == "johndoe@gmail.com"
    assert normalize_email("johndoe+@gmail.com") == "johndoe@gmail.com"


def test_adversarial_non_gmail_handling():
    # Non-Gmail domains should strip +tag but preserve internal dots
    assert normalize_email("First.Last+tag@company.com") == "first.last@company.com"
    assert normalize_email("First.Last@subdomain.company.com") == "first.last@subdomain.company.com"
    assert normalize_email("First.Middle.Last+newsletter@edu.vn") == "first.middle.last@edu.vn"


def test_adversarial_normalization_quirks_and_bypasses():
    """Probe edge-case inputs for bypasses or unexpected transformations."""
    # 1. Trailing dot in domain (FQDN format)
    # RFC 5321/1035 allows FQDN trailing dot, but normalize_email does not strip it
    fqdn_email = "john.doe@gmail.com."
    fqdn_normalized = normalize_email(fqdn_email)
    # Document current behavior: does not match "johndoe@gmail.com"
    assert fqdn_normalized == "john.doe@gmail.com."

    # 2. Country-code Googlemail domains (e.g. googlemail.co.uk)
    uk_email = "john.doe+tag@googlemail.co.uk"
    uk_normalized = normalize_email(uk_email)
    # Document current behavior: preserves dot and ccTLD domain
    assert uk_normalized == "john.doe@googlemail.co.uk"

    # 3. Subdomain of gmail (e.g. mail.gmail.com)
    sub_email = "john.doe+tag@mail.gmail.com"
    sub_normalized = normalize_email(sub_email)
    assert sub_normalized == "john.doe@mail.gmail.com"

    # 4. Spaces inside local part vs around @
    space_email = "john.doe @ gmail.com"
    space_normalized = normalize_email(space_email)
    assert space_normalized == "john.doe @ gmail.com"


# ============================================================================
# PROBE 3: Asyncio Event Loop Non-Blocking Verification for mail.py
# ============================================================================

@pytest.mark.anyio
async def test_send_code_does_not_block_event_loop_during_slow_smtp():
    """Verify that slow/hanging SMTP does not starve or block concurrent coroutines."""
    sender = SmtpEmailSender(
        host="smtp.example.com",
        port=587,
        username="user",
        password="pass",
        sender="noreply@example.com"
    )

    slow_delay = 0.5  # 500ms blocking SMTP call simulation
    loop_ticks = 0

    async def background_heartbeat():
        nonlocal loop_ticks
        while True:
            await asyncio.sleep(0.01)
            loop_ticks += 1

    def slow_send(*args, **kwargs):
        time.sleep(slow_delay)

    heartbeat_task = asyncio.create_task(background_heartbeat())

    try:
        with patch.object(sender, "_send_blocking", side_effect=slow_send):
            start = time.perf_counter()
            await sender.send_code("dest@example.com", "LOGIN", "123456", datetime.now(timezone.utc))
            elapsed = time.perf_counter() - start

        # The blocking call took at least slow_delay
        assert elapsed >= slow_delay

        # Crucial check: The event loop continued running concurrent tasks during the blocking call!
        # If the loop was blocked synchronously, loop_ticks would be 0 or 1.
        assert loop_ticks >= 20, f"Event loop was blocked! Heartbeat ticks: {loop_ticks}"
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


@pytest.mark.anyio
async def test_send_code_exception_propagation_and_safety():
    """Verify that SMTP exceptions propagate cleanly to caller without corrupting loop."""
    sender = SmtpEmailSender(
        host="smtp.example.com",
        port=587,
        username="user",
        password="pass",
        sender="noreply@example.com"
    )

    # 1. Timeout / socket.timeout
    with patch.object(sender, "_send_blocking", side_effect=socket.timeout("Connection timed out")):
        with pytest.raises(socket.timeout, match="Connection timed out"):
            await sender.send_code("dest@example.com", "LOGIN", "123456", datetime.now(timezone.utc))

    # 2. SMTPServerDisconnected
    with patch.object(sender, "_send_blocking", side_effect=smtplib.SMTPServerDisconnected("Connection closed unexpectedly")):
        with pytest.raises(smtplib.SMTPServerDisconnected):
            await sender.send_code("dest@example.com", "LOGIN", "123456", datetime.now(timezone.utc))

    # 3. SMTPConnectError
    with patch.object(sender, "_send_blocking", side_effect=smtplib.SMTPConnectError(421, "Service not available")):
        with pytest.raises(smtplib.SMTPConnectError):
            await sender.send_code("dest@example.com", "LOGIN", "123456", datetime.now(timezone.utc))


@pytest.mark.anyio
async def test_send_code_cancellation():
    """Verify that cancelling a send_code coroutine raises CancelledError cleanly."""
    sender = SmtpEmailSender(
        host="smtp.example.com",
        port=587,
        username="user",
        password="pass",
        sender="noreply@example.com"
    )

    def slow_send(*args, **kwargs):
        time.sleep(1.0)

    with patch.object(sender, "_send_blocking", side_effect=slow_send):
        task = asyncio.create_task(sender.send_code("dest@example.com", "LOGIN", "123456", datetime.now(timezone.utc)))
        await asyncio.sleep(0.05)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.anyio
async def test_send_code_high_concurrency():
    """Verify 25 concurrent send_code calls execute across threads without loop starvation."""
    sender = SmtpEmailSender(
        host="smtp.example.com",
        port=587,
        username="user",
        password="pass",
        sender="noreply@example.com"
    )

    def sim_send(*args, **kwargs):
        time.sleep(0.05)

    with patch.object(sender, "_send_blocking", side_effect=sim_send):
        start = time.perf_counter()
        tasks = [
            sender.send_code(f"user{i}@example.com", "LOGIN", "123456", datetime.now(timezone.utc))
            for i in range(25)
        ]
        await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        # 25 tasks with 0.05s each would take 1.25s sequentially.
        # Across thread pool workers, it completes much faster.
        assert elapsed < 1.0, f"Concurrent execution took too long: {elapsed:.2f}s"
