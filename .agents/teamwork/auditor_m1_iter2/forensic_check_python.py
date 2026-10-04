"""Independent forensic audit tests for server/app/mail.py and server/app/security.py."""
import asyncio
import collections.abc
import concurrent.futures
from datetime import datetime, timezone
import inspect
import sys
import threading
import time
from unittest.mock import patch
import warnings

# Ensure project root is in sys.path
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from server.app.mail import SmtpEmailSender, DualModeMailCall
from server.app.security import normalize_email

def log(msg):
    print(f"[AUDIT] {msg}", flush=True)

async def test_dual_mode_mail_event_loop_and_threads():
    log("Checking DualModeMailCall thread execution and event loop non-blocking...")
    sender = SmtpEmailSender(
        host="smtp.audit-test.local",
        port=587,
        username="audit",
        password="secret",
        sender="noreply@audit.local",
    )

    worker_thread_names = []
    def blocking_smtp(recipient, purpose, code, sent_at):
        worker_thread_names.append(threading.current_thread().name)
        time.sleep(0.3)  # 300ms blocking work

    heartbeat_ticks = 0
    stop_heartbeat = asyncio.Event()

    async def heartbeat():
        nonlocal heartbeat_ticks
        while not stop_heartbeat.is_set():
            await asyncio.sleep(0.01)  # 10ms tick
            heartbeat_ticks += 1

    heartbeat_task = asyncio.create_task(heartbeat())

    with patch.object(sender, "_send_blocking", side_effect=blocking_smtp):
        start = time.perf_counter()
        coro = sender.send_code("dest@example.com", "LOGIN", "123456", datetime.now(timezone.utc))
        
        # Verify return type is DualModeMailCall
        assert isinstance(coro, DualModeMailCall), f"Expected DualModeMailCall, got {type(coro)}"
        assert isinstance(coro, collections.abc.Coroutine), "Must be collections.abc.Coroutine"
        assert inspect.iscoroutinefunction(sender.send_code), "send_code must be marked as coroutine function"

        # Await it
        await coro
        elapsed = time.perf_counter() - start

    stop_heartbeat.set()
    await heartbeat_task

    # Verify execution ran on background thread
    assert len(worker_thread_names) == 1, f"Expected 1 call, got {len(worker_thread_names)}"
    assert worker_thread_names[0].startswith("smtp_sender"), f"Thread name unexpected: {worker_thread_names[0]}"
    assert worker_thread_names[0] != threading.current_thread().name, "Executed on main thread! INTEGRITY VIOLATION!"

    # Verify event loop was NOT blocked
    log(f"Elapsed: {elapsed:.3f}s, Heartbeat ticks: {heartbeat_ticks}, Worker thread: {worker_thread_names[0]}")
    assert elapsed >= 0.28, f"Execution too fast: {elapsed}s"
    assert heartbeat_ticks >= 15, f"Event loop was blocked! Only {heartbeat_ticks} ticks recorded during 300ms call!"

    log("DualModeMailCall thread execution and event loop non-blocking: PASS")

def test_sync_caller_safety():
    log("Checking synchronous caller execution without await...")
    sender = SmtpEmailSender(
        host="smtp.audit-test.local",
        port=587,
        username="audit",
        password="secret",
        sender="noreply@audit.local",
    )

    completed = threading.Event()
    def blocking_smtp(recipient, purpose, code, sent_at):
        time.sleep(0.05)
        completed.set()

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        with patch.object(sender, "_send_blocking", side_effect=blocking_smtp):
            # Call synchronously without await
            ret = sender.send_code("sync@example.com", "REGISTER", "999888", datetime.now(timezone.utc))
            # Delete reference to trigger any potential unawaited coroutine warning
            del ret

        # Wait for threadpool execution
        assert completed.wait(timeout=2.0), "Threadpool execution did not complete!"
        
        # Check warnings
        runtime_warnings = [w for w in captured if issubclass(w.category, RuntimeWarning)]
        assert len(runtime_warnings) == 0, f"Unexpected runtime warnings: {runtime_warnings}"

    log("Synchronous caller execution without await: PASS")

async def test_exception_propagation():
    log("Checking exception propagation in DualModeMailCall...")
    sender = SmtpEmailSender(
        host="smtp.audit-test.local",
        port=587,
        username="audit",
        password="secret",
        sender="noreply@audit.local",
    )

    class CustomSmtpError(Exception):
        pass

    def failing_smtp(*args, **kwargs):
        raise CustomSmtpError("Simulated SMTP network disconnect")

    with patch.object(sender, "_send_blocking", side_effect=failing_smtp):
        try:
            await sender.send_code("dest@example.com", "LOGIN", "123456", datetime.now(timezone.utc))
            assert False, "Exception was swallowed! INTEGRITY VIOLATION!"
        except CustomSmtpError:
            log("CustomSmtpError correctly propagated: PASS")

def test_email_normalization_logic():
    log("Forensic testing of normalize_email...")
    test_cases = [
        # (input, expected)
        ("john.doe@gmail.com", "johndoe@gmail.com"),
        ("John.Doe@Gmail.Com", "johndoe@gmail.com"),
        ("  john.doe+test@gmail.com  ", "johndoe@gmail.com"),
        ("j.o.h.n.d.o.e+newsletter+promo@gmail.com", "johndoe@gmail.com"),
        ("john.doe@googlemail.com", "johndoe@gmail.com"),
        ("user+tag@domain.org", "user@domain.org"),
        ("User.Name+Tag@Domain.Org", "user.name@domain.org"),
        ("plain_username", "plain_username"),
        ("  OPERATOR_1  ", "operator_1"),
        ("", ""),
        ("@", "@"),
        ("@gmail.com", "@gmail.com"),
        ("+tag@gmail.com", "@gmail.com"),
    ]

    for raw, expected in test_cases:
        actual = normalize_email(raw)
        assert actual == expected, f"Failed for {raw}: got {actual!r}, want {expected!r}"

    # Verify no hardcoded dictionary bypass in normalize_email
    import inspect
    src = inspect.getsource(normalize_email)
    assert "john.doe" not in src, "Hardcoded test string found in normalize_email!"
    assert "johndoe" not in src, "Hardcoded test string found in normalize_email!"
    log("Email normalization logic verification: PASS")

async def main():
    log("=== STARTING INDEPENDENT FORENSIC TESTS (PYTHON) ===")
    await test_dual_mode_mail_event_loop_and_threads()
    test_sync_caller_safety()
    await test_exception_propagation()
    test_email_normalization_logic()
    log("=== ALL PYTHON FORENSIC TESTS PASSED ===")

if __name__ == "__main__":
    asyncio.run(main())
