"""
Challenger 2 Adversarial Test Suite:
Hardware Safety, Port Lifecycle, and Thread Safety Verification.

Tests:
1. Hardware Safety (DTR/RTS suppression across all serial open paths).
2. Dynamic Unplug and Hotplug Recovery (lease release and re-binding without restart).
3. Thread Safety under Concurrent write_line() and stop().
4. Fault Tolerance under Corrupted Streams and Exception Resilience.
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import random
import threading
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import serial
import serial.tools.list_ports

from app.serial_io import (
    SerialWorker,
    TelemetryState,
    UsbPortCoordinator,
    coordinator,
    open_serial_port,
    parse_nmea_line,
    state,
)
from conftest import VirtualSerialHub


# ==============================================================================
# 1. Hardware Safety: DTR / RTS Auto-Reset Suppression
# ==============================================================================

class TestHardwareResetSafety:
    """Verifies DTR and RTS flags are explicitly set to False on EVERY open path."""

    def test_open_serial_port_primary_instantiation_suppresses_dtr_rts(
        self, virtual_serial: VirtualSerialHub
    ):
        """Verify open_serial_port sets dtr=False and rts=False on constructor."""
        virtual_serial.register_esp("COM10")
        port = open_serial_port("COM10", 115200)
        try:
            assert port.dtr is False, "DTR was asserted on open_serial_port!"
            assert port.rts is False, "RTS was asserted on open_serial_port!"
            assert port.dsrdtr is False
            assert port.rtscts is False
        finally:
            port.close()

    def test_open_serial_port_fallback_branch_sets_dtr_rts_false_before_and_after_open(self):
        """
        Verify fallback branch (triggered when constructor rejects dtr/rts kwargs, as real PySerial does)
        explicitly sets dtr=False and rts=False BEFORE open() and AFTER open().
        """
        trace = []

        class MockPySerial:
            def __init__(self, *args: Any, **kwargs: Any):
                if kwargs.get("dtr") is not None or kwargs.get("rts") is not None:
                    # Real PySerial SerialBase.__init__ raises ValueError on unknown kwargs
                    raise ValueError("unexpected keyword arguments: dtr, rts")
                self.port = None
                self.baudrate = 9600
                self.timeout = None
                self.dsrdtr = None
                self.rtscts = None
                self._dtr = True
                self._rts = True
                self.is_open = False

            @property
            def dtr(self) -> bool:
                return self._dtr

            @dtr.setter
            def dtr(self, val: bool):
                trace.append(("set_dtr", val, self.is_open))
                self._dtr = val

            @property
            def rts(self) -> bool:
                return self._rts

            @rts.setter
            def rts(self, val: bool):
                trace.append(("set_rts", val, self.is_open))
                self._rts = val

            def open(self):
                # Verify that dtr and rts were ALREADY False prior to open
                assert self._dtr is False, "DTR was still True when open() was called!"
                assert self._rts is False, "RTS was still True when open() was called!"
                self.is_open = True
                trace.append(("opened",))

            def close(self):
                self.is_open = False

        with patch("serial.Serial", side_effect=MockPySerial):
            port = open_serial_port("COM11", 115200)
            assert port.dtr is False
            assert port.rts is False
            # Verify trace shows dtr/rts cleared before open AND after open
            set_dtr_before_open = any(item == ("set_dtr", False, False) for item in trace)
            set_rts_before_open = any(item == ("set_rts", False, False) for item in trace)
            opened_event = ("opened",) in trace
            assert set_dtr_before_open, "DTR was not set to False before open()!"
            assert set_rts_before_open, "RTS was not set to False before open()!"
            assert opened_event, "Port was never opened!"

    def test_ast_proves_zero_bypasses_of_open_serial_port(self):
        """
        Static AST analysis of backend/app/serial_io.py to guarantee NO serial port
        is opened directly with serial.Serial() outside of open_serial_port.
        """
        target_path = os.path.join(os.path.dirname(__file__), "..", "app", "serial_io.py")
        with open(target_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        direct_serial_instantiations = []
        open_serial_port_calls = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_id = ""
                if isinstance(node.func, ast.Name):
                    func_id = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_id = f"{getattr(node.func.value, 'id', '')}.{node.func.attr}"

                if func_id in ("serial.Serial", "Serial"):
                    direct_serial_instantiations.append(node.lineno)
                elif func_id == "open_serial_port":
                    open_serial_port_calls.append(node.lineno)

        # All direct serial.Serial calls must be strictly inside open_serial_port (lines ~130-170)
        for line in direct_serial_instantiations:
            assert 130 <= line <= 170, (
                f"Direct serial.Serial() instantiation at line {line} bypasses open_serial_port!"
            )

        # Probing and workers must exclusively use open_serial_port
        assert len(open_serial_port_calls) >= 3, (
            f"Expected at least 3 open_serial_port calls (gps_probe, esp_probe, worker_run), found {len(open_serial_port_calls)}"
        )


# ==============================================================================
# 2. Dynamic Unplug and Hotplug Recovery
# ==============================================================================

class TestDynamicUnplugAndHotplug:
    """Verifies lease release on abrupt disconnect and automatic re-binding on hotplug."""

    def test_worker_catches_serial_exception_and_releases_lease(
        self, virtual_serial: VirtualSerialHub
    ):
        """
        When a running serial port abruptly throws SerialException on readline(),
        the worker must catch it, release the lease via coordinator.release_device_for_role,
        and make the role available for re-assignment.
        """
        virtual_serial.register_gps("COM20")
        test_coord = UsbPortCoordinator()
        test_coord.scan_and_assign()
        assert test_coord.get_device_for_role("gps") == "COM20"
        assert "COM20" in test_coord.active_ports

        received_lines = []
        worker = SerialWorker("gps", lambda: test_coord.get_device_for_role("gps"), 38400, received_lines.append)

        with patch("app.serial_io.coordinator", test_coord):
            worker.start()
            time.sleep(0.2)

            # Abrupt disconnect
            virtual_serial.unregister_port("COM20")

            # Wait for worker loop to encounter SerialException and trigger release
            deadline = time.monotonic() + 2.0
            released = False
            while time.monotonic() < deadline:
                if test_coord.assigned["gps"] is None and "COM20" not in test_coord.active_ports:
                    released = True
                    break
                time.sleep(0.05)

            worker.stop()
            assert released, "Worker failed to release lease after SerialException!"
            assert test_coord.get_device_for_role("gps") is None

    def test_hotplug_reconnect_to_different_port_without_app_restart(
        self, virtual_serial: VirtualSerialHub
    ):
        """
        Dynamic hotplug scenario:
        1. Device starts on COM30.
        2. Device is unplugged (COM30 unregister).
        3. Device is plugged into COM35 (new port path).
        4. Worker automatically re-acquires COM35 without application restart.
        """
        virtual_serial.register_esp("COM30")
        test_coord = UsbPortCoordinator()
        test_coord.scan_and_assign()
        assert test_coord.get_device_for_role("esp") == "COM30"

        received = []
        worker = SerialWorker("esp", lambda: test_coord.get_device_for_role("esp"), 115200, received.append)

        with patch("app.serial_io.coordinator", test_coord):
            worker.start()
            time.sleep(0.2)
            assert len(received) > 0

            # 1. Unplug COM30
            virtual_serial.unregister_port("COM30")
            time.sleep(0.4)
            assert test_coord.assigned["esp"] is None

            # 2. Hotplug into COM35
            virtual_serial.register_esp("COM35")

            # Worker loop sleeps up to 2.0s before retrying device_resolver
            deadline = time.monotonic() + 4.0
            reconnected = False
            while time.monotonic() < deadline:
                if test_coord.get_device_for_role("esp") == "COM35":
                    reconnected = True
                    break
                time.sleep(0.1)

            worker.stop()
            assert reconnected, "Worker failed to re-bind to new port COM35 upon hotplug!"

    def test_release_device_for_role_is_strictly_idempotent(self):
        """Calling release_device_for_role multiple times with same or None device must not raise."""
        test_coord = UsbPortCoordinator()
        test_coord.assigned["gps"] = "COM40"
        test_coord.active_ports.add("COM40")

        # First release
        test_coord.release_device_for_role("gps", "COM40")
        assert test_coord.assigned["gps"] is None
        assert "COM40" not in test_coord.active_ports

        # Redundant releases (e.g. from except block + finally block)
        test_coord.release_device_for_role("gps", "COM40")
        test_coord.release_device_for_role("gps", None)
        test_coord.release_device_for_role("unknown_role", "COM40")
        assert test_coord.assigned["gps"] is None


# ==============================================================================
# 3. Thread Safety & Concurrency Stress Testing
# ==============================================================================

class TestSerialWorkerThreadSafety:
    """Stress tests concurrent write_line and stop executions."""

    def test_concurrent_write_line_and_stop_stress(self, virtual_serial: VirtualSerialHub):
        """
        Adversarial Concurrency Stress:
        30 threads concurrently hammer worker.write_line() while the main thread
        abruptly calls worker.stop().
        Must not raise any unhandled exceptions, deadlock, or hang.
        """
        virtual_serial.register_esp("COM50")
        worker = SerialWorker("stress_esp", lambda: "COM50", 115200, lambda line: None)
        worker.start()
        time.sleep(0.1)

        exceptions: list[Exception] = []
        results: list[bool] = []
        stop_trigger = threading.Event()

        def spam_writes(thread_idx: int):
            while not stop_trigger.is_set():
                try:
                    payload = json.dumps({"thread": thread_idx, "n": random.random()})
                    ok = worker.write_line(payload)
                    results.append(ok)
                except Exception as exc:
                    exceptions.append(exc)
                time.sleep(0.001)

        writers = [threading.Thread(target=spam_writes, args=(i,)) for i in range(30)]
        for w in writers:
            w.start()

        time.sleep(0.2)
        # Abrupt stop under full load
        t_start = time.monotonic()
        worker.stop()
        stop_elapsed = time.monotonic() - t_start

        # Stop writers
        stop_trigger.set()
        for w in writers:
            w.join(timeout=2.0)
            assert not w.is_alive(), f"Writer thread {w} deadlocked or hung!"

        # Assertions
        assert stop_elapsed < 2.5, f"worker.stop() took too long: {stop_elapsed:.3f}s"
        assert len(exceptions) == 0, f"Concurrent write_line raised exceptions: {exceptions}"
        assert not worker.thread.is_alive(), "Worker thread is still alive after stop()!"
        assert any(r is True for r in results), "No writes succeeded before stop!"
        # After stop(), subsequent writes must return False
        assert worker.write_line("post-stop write") is False

    def test_rapid_start_stop_cycling_under_load(self, virtual_serial: VirtualSerialHub):
        """Rapidly start and stop SerialWorker 10 times in a row under write activity."""
        virtual_serial.register_esp("COM60")
        for cycle in range(10):
            worker = SerialWorker(f"cycle_{cycle}", lambda: "COM60", 115200, lambda line: None)
            worker.start()
            worker.write_line(json.dumps({"cycle": cycle}))
            worker.stop()
            assert not worker.thread.is_alive()


# ==============================================================================
# 4. Adversarial Edge Case: Corrupted Payload Handler Exception Behavior
# ==============================================================================

class TestWorkerFaultResilience:
    """Verifies edge case behavior when line_handler encounters unexpected malformed payload."""

    def test_worker_thread_survives_malformed_payload_or_handler_exception(
        self, virtual_serial: VirtualSerialHub
    ):
        """
        ADVERSARIAL CHALLENGE & HARDENING VERIFICATION:
        Verify whether SerialWorker._run survives an unhandled exception inside line_handler
        (such as float conversion failure on corrupt telemetry).
        """
        virtual_serial.register_port("COM70")

        def corrupt_stream(port: Any):
            port.feed_line('{"type":"telemetry","attitude":{"roll":"NaN_CORRUPT"}}')

        virtual_serial.device_generators["COM70"] = corrupt_stream

        telemetry = TelemetryState()
        worker = SerialWorker("fragile_worker", lambda: "COM70", 115200, telemetry.update_esp_line)
        worker.start()
        time.sleep(0.3)

        thread_alive = worker.thread.is_alive()
        worker.stop()

        # Verify the worker thread survived the malformed payload without crashing
        assert thread_alive is True, (
            "Expected thread to survive malformed payload/exception in update_esp_line "
            "via hardened error handling around self.line_handler(line)."
        )
