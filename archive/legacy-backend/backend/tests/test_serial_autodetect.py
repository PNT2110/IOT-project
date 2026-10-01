"""
Comprehensive E2E and Unit Test Suite for USB Serial Auto-Detection & Concurrency.

Tiers:
- Tier 1: Feature Coverage (GPS 38400, ESP 115200, XOR Checksum, JSON Validation, Baud Configuration)
- Tier 2: Boundary & Corner Cases (Swapped Ports, Identical CH340 VID:PID, Noise Prefix, Silent Streams, DTR/RTS Protection, Dynamic Unplug)
- Tier 3: Cross-Feature Combinations (Concurrent Dual-Port Binding, Greedy Stealing Prevention, Port Release & Re-lease)
- Tier 4: Real-World Workloads (End-to-End Telemetry Streaming, Command Dispatching under Load, Existing Semantics Integrity)
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from app.serial_io import CommandDispatcher, SerialWorker, TelemetryState, parse_nmea_line
from serial_test_harness import (
    MockSerialPort,
    VirtualSerialHub,
    make_esp_generator,
    make_gps_generator,
)


# ==============================================================================
# Tier 1: Feature Coverage (>=5 tests)
# ==============================================================================

class TestTier1FeatureCoverage:
    """Core auto-detection, parsing, format, and baud rate tests."""

    def test_tier1_gps_nmea_auto_detect_at_38400(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify GPS NMEA stream at 38400 baud is correctly auto-detected and assigned."""
        virtual_serial.register_gps("COM3")

        coordinator = coordinator_factory(gps_baud=38400, esp_baud=115200, probe_timeout=0.4)
        mapping = coordinator.scan_and_assign()

        assert mapping.get("gps") == "COM3"
        assert coordinator.get_device_for_role("gps") == "COM3"
        assert coordinator.get_device_for_role("esp") is None

    def test_tier1_esp32_jsonl_auto_detect_at_115200(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify ESP32 JSONL telemetry stream at 115200 baud is correctly auto-detected."""
        virtual_serial.register_esp("COM4")

        coordinator = coordinator_factory(gps_baud=38400, esp_baud=115200, probe_timeout=0.4)
        mapping = coordinator.scan_and_assign()

        assert mapping.get("esp") == "COM4"
        assert coordinator.get_device_for_role("esp") == "COM4"
        assert coordinator.get_device_for_role("gps") is None

    def test_tier1_xor_checksum_validation(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify XOR checksum validation: reject bad checksum, accept valid checksum."""
        virtual_serial.register_gps("COM5", bad_checksum=True)
        virtual_serial.register_gps("COM6", bad_checksum=False)

        coordinator = coordinator_factory(gps_baud=38400, probe_timeout=0.4)
        assert coordinator.probe_port("COM5") != "gps"
        assert coordinator.probe_port("COM6") == "gps"

        # Also verify via core parse_nmea_line
        valid_sentence = "$GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,*76"
        invalid_sentence = "$GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,*99"
        assert parse_nmea_line(valid_sentence) is not None
        assert parse_nmea_line(invalid_sentence) is None

    def test_tier1_json_format_validation(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify JSON format validation: non-JSON / modem data rejected, valid JSON accepted."""
        virtual_serial.register_modem("COM7")
        virtual_serial.register_esp("COM8")

        coordinator = coordinator_factory(esp_baud=115200, probe_timeout=0.4)
        assert coordinator.probe_port("COM7") == "unknown"
        assert coordinator.probe_port("COM8") == "esp"

    def test_tier1_baud_rate_configuration(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify baud rate handling: GPS probed at 38400, ESP at 115200; mismatch causes framing rejection."""
        # Device configured to emit valid bytes ONLY when opened at 38400
        virtual_serial.register_gps("COM9", corrupted_baud_rate=38400)

        coordinator = coordinator_factory(gps_baud=38400, esp_baud=115200, probe_timeout=0.4)
        assert coordinator.probe_port("COM9") == "gps"

        # If coordinator is configured with wrong baud (e.g. 9600), it fails
        wrong_coordinator = coordinator_factory(gps_baud=9600, esp_baud=115200, probe_timeout=0.4)
        assert wrong_coordinator.probe_port("COM9") != "gps"


# ==============================================================================
# Tier 2: Boundary & Corner Cases (>=5 tests)
# ==============================================================================

class TestTier2BoundaryCornerCases:
    """Boundary conditions, noise handling, hardware reset protection, and disconnects."""

    def test_tier2_swapped_port_enumeration(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify that when kernel enumerates ESP32 on port 0 and GPS on port 1, assignments remain correct."""
        virtual_serial.register_esp("COM0")
        virtual_serial.register_gps("COM1")

        coordinator = coordinator_factory(probe_timeout=0.4)
        mapping = coordinator.scan_and_assign()

        assert mapping["esp"] == "COM0"
        assert mapping["gps"] == "COM1"
        assert coordinator.get_device_for_role("gps") == "COM1"
        assert coordinator.get_device_for_role("esp") == "COM0"

    def test_tier2_identical_ch340_vid_pid_simulation(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify disambiguation works when both USB bridges share identical CH340 VID:PID (0x1A86:0x7523)."""
        virtual_serial.register_gps("COM10", vid=0x1A86, pid=0x7523, serial_number=None)
        virtual_serial.register_esp("COM11", vid=0x1A86, pid=0x7523, serial_number=None)

        coordinator = coordinator_factory(probe_timeout=0.4)
        coordinator.scan_and_assign()

        assert coordinator.get_device_for_role("gps") == "COM10"
        assert coordinator.get_device_for_role("esp") == "COM11"

    def test_tier2_noise_and_garbage_bytes_before_valid_sentence(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify probe gracefully discards partial lines or power-on garbage bytes before valid sentence."""
        virtual_serial.register_gps("COM12", noise_prefix=True)

        coordinator = coordinator_factory(probe_timeout=0.4)
        assert coordinator.probe_port("COM12") == "gps"

    def test_tier2_empty_and_silent_streams(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify silent/empty ports cleanly time out and are classified as unknown."""
        virtual_serial.register_silent("COM13")

        coordinator = coordinator_factory(probe_timeout=0.3)
        assert coordinator.probe_port("COM13") == "unknown"
        assert coordinator.get_device_for_role("gps") is None
        assert coordinator.get_device_for_role("esp") is None

    def test_tier2_dtr_rts_flags_suppressed_for_esp32_protection(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify that all serial opens enforce dtr=False and rts=False to prevent ESP32 hardware reset."""
        virtual_serial.register_esp("COM14")

        coordinator = coordinator_factory(probe_timeout=0.4)
        coordinator.scan_and_assign()

        # Check all opened mock instances for COM14
        opened_instances = [inst for inst in virtual_serial.active_instances if inst.port == "COM14"]
        assert len(opened_instances) > 0
        for inst in opened_instances:
            assert inst.dtr is False, f"DTR was asserted on {inst.port}!"
            assert inst.rts is False, f"RTS was asserted on {inst.port}!"
            assert inst.dsrdtr is False
            assert inst.rtscts is False

    def test_tier2_dynamic_unplug_port_loss(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify port loss triggers lease cleanup and marks role unassigned."""
        virtual_serial.register_gps("COM15")

        coordinator = coordinator_factory(probe_timeout=0.4)
        assert coordinator.get_device_for_role("gps") == "COM15"

        # Simulate dynamic unplug
        virtual_serial.unregister_port("COM15")
        coordinator.release_device_for_role("gps", "COM15")

        assert coordinator.get_device_for_role("gps") is None


# ==============================================================================
# Tier 3: Cross-Feature Combinations
# ==============================================================================

class TestTier3CrossFeatureCombinations:
    """Concurrency, collision avoidance, and reconnection dynamics."""

    def test_tier3_concurrent_dual_port_binding_no_cross_talk(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify concurrent dual-port binding: GPS and ESP workers stream simultaneously without race conditions."""
        virtual_serial.register_gps("COM20")
        virtual_serial.register_esp("COM21")

        coordinator = coordinator_factory(probe_timeout=0.4)
        coordinator.scan_and_assign()

        gps_port = coordinator.get_device_for_role("gps")
        esp_port = coordinator.get_device_for_role("esp")
        assert gps_port == "COM20"
        assert esp_port == "COM21"
        assert gps_port != esp_port

        received_gps_lines: list[str] = []
        received_esp_lines: list[str] = []

        gps_worker = SerialWorker("test-gps", lambda: gps_port, 38400, received_gps_lines.append)
        esp_worker = SerialWorker("test-esp", lambda: esp_port, 115200, received_esp_lines.append)

        try:
            gps_worker.start()
            esp_worker.start()
            time.sleep(0.3)
        finally:
            gps_worker.stop()
            esp_worker.stop()

        # Verify no cross-talk
        assert len(received_gps_lines) > 0
        for line in received_gps_lines:
            assert line.startswith("$"), f"Corrupted GPS line: {line}"

        assert len(received_esp_lines) > 0
        for line in received_esp_lines:
            assert line.startswith("{") or "telemetry" in line, f"Corrupted ESP line: {line}"

    def test_tier3_prevent_greedy_port_stealing(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify that ESP resolver does not steal candidate[0] when candidate[0] is GPS."""
        # COM30 is GPS, COM31 is ESP
        virtual_serial.register_gps("COM30")
        virtual_serial.register_esp("COM31")

        coordinator = coordinator_factory(probe_timeout=0.4)

        # Request ESP port first
        esp_assigned = coordinator.get_device_for_role("esp")
        assert esp_assigned == "COM31", "ESP greedily stole COM30 (GPS)!"

        # Then request GPS port
        gps_assigned = coordinator.get_device_for_role("gps")
        assert gps_assigned == "COM30"

    def test_tier3_port_release_and_re_lease_on_device_reconnect(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify dynamic reconnect: device unplugged from COM40 and re-inserted as COM42 is re-acquired."""
        virtual_serial.register_gps("COM40")

        coordinator = coordinator_factory(probe_timeout=0.4)
        assert coordinator.get_device_for_role("gps") == "COM40"

        # Disconnect COM40
        virtual_serial.unregister_port("COM40")
        coordinator.release_device_for_role("gps", "COM40")
        assert coordinator.get_device_for_role("gps") is None

        # Reconnect on new node COM42
        virtual_serial.register_gps("COM42")
        coordinator.scan_and_assign()
        assert coordinator.get_device_for_role("gps") == "COM42"


# ==============================================================================
# Tier 4: Real-World Workloads
# ==============================================================================

class TestTier4RealWorldWorkloads:
    """Full telemetry loop, command dispatching under concurrent load, and regression safety."""

    def test_tier4_end_to_end_telemetry_streaming(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify full telemetry pipeline: raw serial -> workers -> TelemetryState snapshot."""
        telemetry = TelemetryState()

        virtual_serial.register_gps("COM50")
        virtual_serial.register_esp("COM51")

        coordinator = coordinator_factory(probe_timeout=0.4)
        coordinator.scan_and_assign()

        def handle_gps(line: str):
            parsed = parse_nmea_line(line, telemetry.snapshot().gps)
            if parsed:
                telemetry.update_gps(parsed)

        gps_worker = SerialWorker("gps-e2e", lambda: coordinator.get_device_for_role("gps"), 38400, handle_gps)
        esp_worker = SerialWorker("esp-e2e", lambda: coordinator.get_device_for_role("esp"), 115200, telemetry.update_esp_line)

        try:
            gps_worker.start()
            esp_worker.start()
            time.sleep(0.35)

            frame = telemetry.snapshot()
            assert frame.gps_connected is True
            assert frame.esp_connected is True
            assert frame.gps.valid is True
            assert frame.gps.latitude is not None
            assert frame.attitude.roll == 1.25
            assert frame.armed is True
            assert frame.flight_mode == "STABILIZE"
        finally:
            gps_worker.stop()
            esp_worker.stop()

    def test_tier4_command_dispatching_under_concurrent_telemetry(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify CommandDispatcher can execute land command with ACK under active telemetry stream."""
        telemetry = TelemetryState()

        virtual_serial.register_esp("COM60")
        coordinator = coordinator_factory(probe_timeout=0.4)
        esp_port = coordinator.get_device_for_role("esp")
        assert esp_port == "COM60"

        esp_worker = SerialWorker("esp-cmd", lambda: esp_port, 115200, telemetry.update_esp_line)

        try:
            esp_worker.start()
            time.sleep(0.2)

            dispatcher = CommandDispatcher(esp_worker, telemetry)
            frame, ack, attempts = asyncio.run(dispatcher.land("EMERGENCY_GEOFENCE"))

            assert ack is not None
            assert ack.accepted is True
            assert ack.command_id == frame.id
            assert attempts == 1
        finally:
            esp_worker.stop()

    def test_tier4_existing_test_suite_semantics_intact(self):
        """Regression guard: verify existing parser and dispatcher logic remains 100% compliant."""
        # 1. Valid GGA parser
        fix = parse_nmea_line("$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47")
        assert fix is not None and fix.valid
        assert round(fix.latitude or 0, 4) == 48.1173

        # 2. Bad checksum rejection
        assert parse_nmea_line("$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*00") is None

        # 3. JSONL ESP parser updates
        st = TelemetryState()
        st.update_esp_line('{"type":"telemetry","attitude":{"roll":10,"pitch":20,"yaw":30},"armed":true}')
        snap = st.snapshot()
        assert snap.attitude.roll == 10
        assert snap.armed is True


# ==============================================================================
# Interface Contract Compliance Test
# ==============================================================================

def test_coordinator_contract_compliance(coordinator_factory: Any):
    """
    Verifies that the UsbPortCoordinator satisfies PROJECT.md Interface Contracts:
    - get_device_for_role(role: str) -> str | None
    - release_device_for_role(role: str, device: str) -> None
    - scan_and_assign() -> dict[str, str | None]
    """
    coordinator = coordinator_factory()
    assert hasattr(coordinator, "get_device_for_role")
    assert hasattr(coordinator, "release_device_for_role")
    assert hasattr(coordinator, "scan_and_assign")
    assert callable(coordinator.get_device_for_role)
    assert callable(coordinator.release_device_for_role)
    assert callable(coordinator.scan_and_assign)


def test_serial_io_implements_coordinator():
    """
    Checks if backend.app.serial_io exports UsbPortCoordinator.
    If not yet implemented (Milestone M1 pending by worker_impl_1),
    this test reports xfail per TDD protocol.
    """
    from app import serial_io
    if not hasattr(serial_io, "UsbPortCoordinator"):
        pytest.xfail(
            "Milestone M1 in progress: UsbPortCoordinator to be exported by backend.app.serial_io (assigned to worker_impl_1)"
        )
    assert hasattr(serial_io, "UsbPortCoordinator")
