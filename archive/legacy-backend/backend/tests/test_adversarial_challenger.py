"""
Tier 5 Adversarial & Stress Testing Suite by Challenger 1.
Probes:
1. High-concurrency calls to scan_and_assign() and get_device_for_role() from multiple threads.
2. Port contention & mutual exclusion under simultaneous race conditions.
3. Inverted port order (/dev/ttyUSB0=ESP, /dev/ttyUSB1=GPS) preventing greedy index-based theft.
4. Checksum corruption and byte truncation during probing and active streaming.
"""
from __future__ import annotations

import concurrent.futures
import threading
import time
from typing import Any

import pytest

from app.models import GpsFix
from app.serial_io import (
    SerialWorker,
    TelemetryState,
    UsbPortCoordinator,
    is_valid_nmea_checksum,
    parse_nmea_line,
)
from serial_test_harness import (
    MockSerialPort,
    VirtualSerialHub,
    make_esp_generator,
    make_gps_generator,
)


# ==============================================================================
# 1. High-Concurrency Stress Tests
# ==============================================================================

class TestAdversarialConcurrency:
    """Stress-test UsbPortCoordinator under heavy multi-threaded contention."""

    def test_concurrent_scan_and_assign_50_threads(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """50 threads simultaneously hammer scan_and_assign() with a synchronized barrier."""
        virtual_serial.register_gps("/dev/ttyUSB1")
        virtual_serial.register_esp("/dev/ttyUSB0")

        coordinator = coordinator_factory(probe_timeout=0.3)
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        results: list[dict[str, str | None]] = []
        errors: list[Exception] = []

        def worker_scan():
            try:
                barrier.wait(timeout=5.0)
                res = coordinator.scan_and_assign()
                results.append(res)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker_scan) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"Exceptions occurred during concurrent scan: {errors}"
        assert len(results) == num_threads

        # Invariant: Every thread sees the exact same consistent port assignment
        for res in results:
            assert res.get("gps") == "/dev/ttyUSB1"
            assert res.get("esp") == "/dev/ttyUSB0"
            assert res.get("gps") != res.get("esp")

    def test_concurrent_mixed_role_resolution(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """30 threads racing: some call get_device_for_role('gps'), some 'esp', some scan_and_assign()."""
        virtual_serial.register_gps("/dev/ttyUSB_GPS")
        virtual_serial.register_esp("/dev/ttyUSB_ESP")

        coordinator = coordinator_factory(probe_timeout=0.3)
        num_threads = 30
        barrier = threading.Barrier(num_threads)
        gps_results: list[str | None] = []
        esp_results: list[str | None] = []
        errors: list[Exception] = []

        def worker_func(role: str):
            try:
                barrier.wait(timeout=5.0)
                if role == "gps":
                    dev = coordinator.get_device_for_role("gps")
                    gps_results.append(dev)
                elif role == "esp":
                    dev = coordinator.get_device_for_role("esp")
                    esp_results.append(dev)
                else:
                    mapping = coordinator.scan_and_assign()
                    gps_results.append(mapping.get("gps"))
                    esp_results.append(mapping.get("esp"))
            except Exception as e:
                errors.append(e)

        threads: list[threading.Thread] = []
        for i in range(num_threads):
            role_choice = "gps" if i % 3 == 0 else ("esp" if i % 3 == 1 else "both")
            threads.append(threading.Thread(target=worker_func, args=(role_choice,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"Errors in concurrent resolution: {errors}"
        for g in gps_results:
            assert g == "/dev/ttyUSB_GPS", f"GPS assigned invalid port: {g}"
        for e in esp_results:
            assert e == "/dev/ttyUSB_ESP", f"ESP assigned invalid port: {e}"

    def test_concurrent_release_and_reassignment_race(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Interleaved calls to release_device_for_role and scan_and_assign do not corrupt state."""
        virtual_serial.register_gps("COM1")
        virtual_serial.register_esp("COM2")

        coordinator = coordinator_factory(probe_timeout=0.3)
        coordinator.scan_and_assign()

        stop_event = threading.Event()
        errors: list[Exception] = []

        def release_worker():
            while not stop_event.is_set():
                try:
                    coordinator.release_device_for_role("gps", "COM1")
                    time.sleep(0.01)
                except Exception as e:
                    errors.append(e)

        def scan_worker():
            while not stop_event.is_set():
                try:
                    coordinator.scan_and_assign()
                    dev_gps = coordinator.get_device_for_role("gps")
                    dev_esp = coordinator.get_device_for_role("esp")
                    # Invariant: GPS and ESP can NEVER be the same port
                    if dev_gps is not None and dev_esp is not None:
                        assert dev_gps != dev_esp, f"Collision: GPS={dev_gps}, ESP={dev_esp}"
                    assert dev_esp == "COM2"
                    time.sleep(0.01)
                except Exception as e:
                    errors.append(e)

        t1 = threading.Thread(target=release_worker)
        t2 = threading.Thread(target=scan_worker)
        t3 = threading.Thread(target=scan_worker)

        t1.start()
        t2.start()
        t3.start()

        time.sleep(0.5)
        stop_event.set()

        t1.join(timeout=2.0)
        t2.join(timeout=2.0)
        t3.join(timeout=2.0)

        assert not errors, f"Errors during interleaved release/reassign: {errors}"


# ==============================================================================
# 2. Port Contention & Mutual Exclusion
# ==============================================================================

class TestAdversarialPortContention:
    """Ensure GPS and ESP workers never seize each other's ports under race conditions."""

    def test_single_gps_port_under_contention(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """When only a single GPS port exists, ESP worker must NEVER acquire it."""
        virtual_serial.register_gps("/dev/ttyUSB_ONLY_GPS")

        coordinator = coordinator_factory(probe_timeout=0.3)
        num_trials = 20
        barrier = threading.Barrier(2)

        def try_gps(res_list):
            barrier.wait()
            res_list.append(coordinator.get_device_for_role("gps"))

        def try_esp(res_list):
            barrier.wait()
            res_list.append(coordinator.get_device_for_role("esp"))

        for _ in range(num_trials):
            coordinator.reset()
            barrier.reset()
            gps_res, esp_res = [], []
            t_gps = threading.Thread(target=try_gps, args=(gps_res,))
            t_esp = threading.Thread(target=try_esp, args=(esp_res,))

            t_gps.start()
            t_esp.start()
            t_gps.join(timeout=2.0)
            t_esp.join(timeout=2.0)

            assert gps_res[0] == "/dev/ttyUSB_ONLY_GPS"
            assert esp_res[0] is None, f"ESP illegally grabbed GPS port: {esp_res[0]}"

    def test_single_esp_port_under_contention(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """When only a single ESP port exists, GPS worker must NEVER acquire it."""
        virtual_serial.register_esp("/dev/ttyUSB_ONLY_ESP")

        coordinator = coordinator_factory(probe_timeout=0.3)
        num_trials = 20
        barrier = threading.Barrier(2)

        def try_gps(res_list):
            barrier.wait()
            res_list.append(coordinator.get_device_for_role("gps"))

        def try_esp(res_list):
            barrier.wait()
            res_list.append(coordinator.get_device_for_role("esp"))

        for _ in range(num_trials):
            coordinator.reset()
            barrier.reset()
            gps_res, esp_res = [], []
            t_gps = threading.Thread(target=try_gps, args=(gps_res,))
            t_esp = threading.Thread(target=try_esp, args=(esp_res,))

            t_gps.start()
            t_esp.start()
            t_gps.join(timeout=2.0)
            t_esp.join(timeout=2.0)

            assert esp_res[0] == "/dev/ttyUSB_ONLY_ESP"
            assert gps_res[0] is None, f"GPS illegally grabbed ESP port: {gps_res[0]}"

    def test_mutual_exclusion_invariant_under_rapid_cycles(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Verify assigned['gps'] == assigned['esp'] is IMPOSSIBLE over 50 rapid scan/reset cycles."""
        virtual_serial.register_gps("/dev/ttyUSB0")
        virtual_serial.register_esp("/dev/ttyUSB1")

        coordinator = coordinator_factory(probe_timeout=0.2)

        for cycle in range(50):
            coordinator.reset()
            mapping = coordinator.scan_and_assign()
            gps = mapping.get("gps")
            esp = mapping.get("esp")

            if gps is not None and esp is not None:
                assert gps != esp, f"Cycle {cycle}: Mutual exclusion violated! Both assigned to {gps}"
            assert gps == "/dev/ttyUSB0"
            assert esp == "/dev/ttyUSB1"


# ==============================================================================
# 3. Inverted Port Order & Anti-Greedy Mapping
# ==============================================================================

class TestAdversarialInvertedPortOrder:
    """Verify system handles inverted device enumeration without greedy theft."""

    def test_inverted_order_ttyusb0_is_esp_ttyusb1_is_gps(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """
        Kernel enumerates ESP on /dev/ttyUSB0 and GPS on /dev/ttyUSB1.
        Verify GPS caller does NOT blindly take ttyUSB0 (greedy index 0).
        """
        virtual_serial.register_esp("/dev/ttyUSB0")
        virtual_serial.register_gps("/dev/ttyUSB1")

        coordinator = coordinator_factory(probe_timeout=0.3)

        # 1. GPS queries first
        gps_port = coordinator.get_device_for_role("gps")
        assert gps_port == "/dev/ttyUSB1", f"GPS greedily seized ESP port /dev/ttyUSB0! Got: {gps_port}"

        # 2. ESP queries second
        esp_port = coordinator.get_device_for_role("esp")
        assert esp_port == "/dev/ttyUSB0"

    def test_inverted_order_esp_queries_first(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """When ESP queries first on inverted ports, it grabs ttyUSB0 and leaves ttyUSB1 for GPS."""
        virtual_serial.register_esp("/dev/ttyUSB0")
        virtual_serial.register_gps("/dev/ttyUSB1")

        coordinator = coordinator_factory(probe_timeout=0.3)

        esp_port = coordinator.get_device_for_role("esp")
        assert esp_port == "/dev/ttyUSB0"

        gps_port = coordinator.get_device_for_role("gps")
        assert gps_port == "/dev/ttyUSB1"

    def test_complex_multi_device_order_with_noise_and_modems(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """
        Candidates:
        /dev/ttyUSB0 -> silent port
        /dev/ttyUSB1 -> AT modem
        /dev/ttyUSB2 -> ESP32
        /dev/ttyUSB3 -> GPS (38400 baud)
        """
        virtual_serial.register_silent("/dev/ttyUSB0")
        virtual_serial.register_modem("/dev/ttyUSB1")
        virtual_serial.register_esp("/dev/ttyUSB2")
        virtual_serial.register_gps("/dev/ttyUSB3")

        coordinator = coordinator_factory(probe_timeout=0.3)
        mapping = coordinator.scan_and_assign()

        assert mapping.get("esp") == "/dev/ttyUSB2"
        assert mapping.get("gps") == "/dev/ttyUSB3"
        assert coordinator.get_device_for_role("gps") == "/dev/ttyUSB3"
        assert coordinator.get_device_for_role("esp") == "/dev/ttyUSB2"


# ==============================================================================
# 4. Checksum Corruption & Byte Truncation
# ==============================================================================

class TestAdversarialChecksumCorruption:
    """Verify strict rejection of corrupt, truncated, or malformed NMEA sentences."""

    @pytest.mark.parametrize(
        "corrupt_nmea",
        [
            # Invalid XOR checksum
            "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*00",
            "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*FF",
            "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*46",  # off-by-one (real is 47)
            "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*48",  # off-by-one
            # Non-hex checksum
            "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*ZZ",
            "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*!@",
            # Truncated sentences
            "$GPGGA,123519,4807.038,N",
            "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*",
            "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*4",  # single hex digit
            # Missing dollar sign
            "GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47",
            # Empty / pure noise
            "",
            "$",
            "$$$$$",
            "\x00\xff\xfe\xca\r\n",
            # Corrupted payload ending in test fixture suffixes *4A or *7B
            "$GPGGA,CORRUPT_PAYLOAD_WITH_RANDOM_DATA*4A",
            "$GNRMC,CORRUPT_PAYLOAD_WITH_RANDOM_DATA*7B",
        ],
    )
    def test_parse_nmea_line_strictly_rejects_corrupt_data(self, corrupt_nmea: str):
        """Every corrupted, malformed, or truncated NMEA string must return None."""
        result = parse_nmea_line(corrupt_nmea)
        assert result is None, f"Corrupted NMEA was accepted: {corrupt_nmea!r} -> {result}"

    def test_is_valid_nmea_checksum_logic(self):
        """Direct unit testing of is_valid_nmea_checksum against edge cases."""
        # Valid checksums
        assert is_valid_nmea_checksum("$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47") is True
        assert is_valid_nmea_checksum("$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A") is True

        # Invalid checksums
        assert is_valid_nmea_checksum("$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*46") is False
        assert is_valid_nmea_checksum("NoDollar*47") is False
        assert is_valid_nmea_checksum("$NoAsterisk47") is False
        assert is_valid_nmea_checksum("$Short*4") is False
        assert is_valid_nmea_checksum("$BadHex*ZZ") is False

    def test_probing_rejects_corrupted_checksum_port(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Port emitting only NMEA sentences with bad checksums must NEVER be classified as GPS."""
        def bad_checksum_generator(port: MockSerialPort):
            # Emits invalid checksum *99 (correct is *47)
            port.feed_line("$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*99")
            port.feed_line("$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*99")

        virtual_serial.register_port("/dev/ttyUSB_CORRUPT_GPS", generator=bad_checksum_generator)

        coordinator = coordinator_factory(probe_timeout=0.3)
        role = coordinator.probe_port("/dev/ttyUSB_CORRUPT_GPS")
        assert role != "gps", f"Corrupt checksum port was classified as GPS: {role}"
        assert role == "unknown"

    def test_probing_rejects_truncated_bytes_port(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """Port emitting chopped/truncated byte fragments must NEVER be classified as GPS."""
        def truncated_generator(port: MockSerialPort):
            port.feed_bytes(b"$GPGGA,123519\r\n")
            port.feed_bytes(b"$GNGGA,partially_cut_off_bytes\r\n")

        virtual_serial.register_port("/dev/ttyUSB_TRUNCATED", generator=truncated_generator)

        coordinator = coordinator_factory(probe_timeout=0.3)
        role = coordinator.probe_port("/dev/ttyUSB_TRUNCATED")
        assert role != "gps"

    def test_probing_non_nmea_frame_with_valid_xor(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """A non-NMEA device emitting proprietary frames ($CUSTOM*XX) with valid XOR should not be classified as GPS."""
        body = "CUSTOM_SENSOR,VALUE1,VALUE2"
        xor_val = 0
        for c in body:
            xor_val ^= ord(c)
        custom_sentence = f"${body}*{xor_val:02X}"

        def sensor_gen(port: MockSerialPort):
            port.feed_line(custom_sentence)

        virtual_serial.register_port("/dev/ttyUSB_CUSTOM", generator=sensor_gen)
        coordinator = coordinator_factory(probe_timeout=0.3)
        role = coordinator.probe_port("/dev/ttyUSB_CUSTOM")
        assert role != "gps", f"Non-NMEA custom frame with valid XOR was misclassified as GPS: {role}"


    def test_active_streaming_with_corrupt_bursts_does_not_poison_telemetry_state(
        self, virtual_serial: VirtualSerialHub, coordinator_factory: Any
    ):
        """
        Under live streaming, bursts of corrupted NMEA lines interspersed between valid lines
        must be discarded cleanly without corrupting the GpsFix coordinates or crashing worker.
        """
        telemetry = TelemetryState()
        valid_line = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"

        def handle_gps(line: str):
            parsed = parse_nmea_line(line, telemetry.snapshot().gps)
            if parsed:
                telemetry.update_gps(parsed)

        # 1. Establish initial good fix
        handle_gps(valid_line)
        initial_fix = telemetry.snapshot().gps
        assert initial_fix.valid is True
        assert round(initial_fix.latitude, 4) == 48.1173
        assert round(initial_fix.longitude, 4) == 11.5167

        # 2. Burst of corrupt data
        corrupted_lines = [
            "$GPGGA,999999,0000.000,N,00000.000,W,1,00,0.0,0.0,M,0.0,M,,*00",  # bad checksum
            "$GPGGA,truncated",
            "\x00\xff\xaa\xbb",
            "$GNRMC,corrupted_burst*ZZ",
        ]
        for c in corrupted_lines:
            handle_gps(c)

        # Verify state was NOT overwritten by corrupt data
        after_corrupt = telemetry.snapshot().gps
        assert after_corrupt.valid is True
        assert round(after_corrupt.latitude, 4) == 48.1173
        assert round(after_corrupt.longitude, 4) == 11.5167

        # 3. Valid update with new coordinates (valid XOR checksum for this line is 0x40)
        new_valid = "$GPGGA,123520,4807.040,N,01131.005,E,1,08,0.9,546.0,M,46.9,M,,*40"
        handle_gps(new_valid)
        updated_fix = telemetry.snapshot().gps
        assert round(updated_fix.latitude, 4) == 48.1173
        assert updated_fix.altitude_m == 546.0

    def test_vulnerability_forged_coordinate_bypass_via_hardcoded_4a_suffix(self):
        """
        VULNERABILITY DEMONSTRATION:
        backend/app/serial_io.py lines 94-98 contain a hardcoded bypass:
            if line.endswith('*4A') or line.endswith('*7B'):
                message = pynmea2.parse(line.split('*')[0], check=False)
        This test proves that a corrupted or forged NMEA sentence with invalid XOR
        checksum ending with '*4A' is accepted and poisons GpsFix coordinates!
        """
        # A corrupted coordinate frame where real XOR is NOT 0x4A, but ending in *4A
        forged_sentence = "$GPGGA,123519,9999.999,N,99999.999,E,1,08,0.9,545.4,M,46.9,M,,*4A"
        
        # Verify that the checksum is indeed corrupt / does not match 0x4A
        assert not is_valid_nmea_checksum(forged_sentence), "Test sanity: sentence should have bad checksum"

        # Under strict validation, parse_nmea_line MUST return None.
        # However, due to the backdoor in serial_io.py, it returns a valid GpsFix with poisoned coordinates!
        parsed = parse_nmea_line(forged_sentence)
        assert parsed is None, (
            f"SECURITY FLAW: Corrupted coordinate sentence with bad checksum was ACCEPTED! "
            f"Poisoned GpsFix: lat={getattr(parsed, 'latitude', None)}, lon={getattr(parsed, 'longitude', None)}, "
            f"valid={getattr(parsed, 'valid', None)}"
        )

