"""
Pytest configuration and shared fixtures for USB Serial Auto-Detection & Concurrency testing.
Provides cross-platform, in-memory duck-typed MockSerialPort and VirtualSerialHub without POSIX pty dependencies.
"""
from __future__ import annotations

import json
import queue
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Generator
from unittest.mock import patch

import pytest
import serial
import serial.tools.list_ports


@dataclass
class MockListPortInfo:
    """Simulates a serial.tools.list_ports.ListPortInfo object."""
    device: str
    description: str = "USB-Serial (CH340)"
    vid: int = 0x1A86
    pid: int = 0x7523
    serial_number: str | None = None
    location: str | None = None

    @property
    def name(self) -> str:
        return Path(self.device).name if "/" in self.device or "\\" in self.device else self.device

    @property
    def hwid(self) -> str:
        sn_part = f" SNR={self.serial_number}" if self.serial_number else ""
        return f"USB VID:PID={self.vid:04X}:{self.pid:04X}{sn_part}"


class MockSerialPort:
    """
    In-memory duck-typed serial port that behaves like serial.Serial.
    Works identically on Windows and Linux without OS drivers or POSIX pty.
    """
    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float | None = 1.0,
        write_timeout: float | None = 1.0,
        dsrdtr: bool = False,
        rtscts: bool = False,
        **kwargs: Any,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.dsrdtr = dsrdtr
        self.rtscts = rtscts
        self.dtr = kwargs.get("dtr", False)
        self.rts = kwargs.get("rts", False)
        self.is_open = True

        self._lock = threading.RLock()
        self._rx_buffer = bytearray()
        self.outbound_data: list[bytes] = []
        self.written_lines: list[str] = []
        self._generator: Callable[[MockSerialPort], None] | None = None

        self.disconnect_on_read = False
        self.disconnect_on_write = False

    def feed_bytes(self, data: bytes) -> None:
        """Inject raw bytes into the simulated receive buffer."""
        with self._lock:
            self._rx_buffer.extend(data)

    def feed_line(self, line: str) -> None:
        """Inject a single CRLF line into the simulated receive buffer."""
        raw = (line.rstrip("\r\n") + "\r\n").encode("ascii", errors="replace")
        self.feed_bytes(raw)

    def reset_input_buffer(self) -> None:
        with self._lock:
            self._rx_buffer.clear()
            if self._generator:
                self._generator(self)

    def reset_output_buffer(self) -> None:
        with self._lock:
            self.outbound_data.clear()

    def readline(self, size: int = -1) -> bytes:
        if not self.is_open:
            raise serial.SerialException(f"Port {self.port} is closed")
        if self.disconnect_on_read:
            self.is_open = False
            raise serial.SerialException(f"Device disconnected on {self.port}")

        start_time = time.monotonic()
        timeout = self.timeout if self.timeout is not None else 1.0

        while self.is_open:
            with self._lock:
                if not self._rx_buffer and self._generator:
                    self._generator(self)

                idx = self._rx_buffer.find(b"\n")
                if idx != -1:
                    line = bytes(self._rx_buffer[: idx + 1])
                    del self._rx_buffer[: idx + 1]
                    return line
                if self._rx_buffer and (size > 0 and len(self._rx_buffer) >= size):
                    chunk = bytes(self._rx_buffer[:size])
                    del self._rx_buffer[:size]
                    return chunk

            if time.monotonic() - start_time >= timeout:
                break
            time.sleep(0.005)

            if self.disconnect_on_read:
                self.is_open = False
                raise serial.SerialException(f"Device disconnected on {self.port}")

        with self._lock:
            data = bytes(self._rx_buffer)
            self._rx_buffer.clear()
            return data

    def read(self, size: int = 1) -> bytes:
        if not self.is_open:
            raise serial.SerialException(f"Port {self.port} is closed")
        if self.disconnect_on_read:
            self.is_open = False
            raise serial.SerialException(f"Device disconnected on {self.port}")

        with self._lock:
            if not self._rx_buffer and self._generator:
                self._generator(self)
            chunk = bytes(self._rx_buffer[:size])
            del self._rx_buffer[:size]
            return chunk

    def write(self, data: bytes) -> int:
        with self._lock:
            if not self.is_open:
                raise serial.SerialException(f"Port {self.port} is closed")
            if self.disconnect_on_write:
                self.is_open = False
                raise serial.SerialException(f"Device write failed on {self.port}")
            self.outbound_data.append(data)
            try:
                line_str = data.decode("utf-8", errors="replace").strip()
                if line_str:
                    self.written_lines.append(line_str)
                    self._handle_device_command(line_str)
            except Exception:
                pass
            return len(data)

    def _handle_device_command(self, line: str) -> None:
        """Simulates autonomous ESP32 ACK reply when receiving JSON command."""
        try:
            payload = json.loads(line)
            if payload.get("type") == "command" or payload.get("command") == "LAND":
                cmd_id = payload.get("id")
                ack = {
                    "version": 1,
                    "type": "ack",
                    "command_id": str(cmd_id),
                    "accepted": True,
                    "message": "COMMAND_ACCEPTED",
                }
                self.feed_line(json.dumps(ack))
        except Exception:
            pass

    def flush(self) -> None:
        pass

    def close(self) -> None:
        with self._lock:
            self.is_open = False

    def __enter__(self) -> MockSerialPort:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


# Standard stream generators for devices
def make_gps_generator(
    valid_sentences: bool = True,
    bad_checksum: bool = False,
    noise_prefix: bool = False,
    corrupted_baud_rate: int | None = None,
) -> Callable[[MockSerialPort], None]:
    def generator(port: MockSerialPort) -> None:
        if corrupted_baud_rate and port.baudrate != corrupted_baud_rate:
            # Baud rate mismatch produces UART framing errors
            port.feed_bytes(b"\x00\xff\xaa\x55\x80\x00\xfe\xca\r\n")
            return
        if noise_prefix:
            port.feed_bytes(b"\xfe\xaa\x12\x00corrupt_boot_bytes\r\n")
        if bad_checksum:
            port.feed_line("$GNGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*00")
        elif valid_sentences:
            port.feed_line("$GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,*76")
            port.feed_line("$GNRMC,123519.00,A,1046.1234,N,10640.5678,E,0.22,120.5,090926,,,A*77")
    return generator


def make_esp_generator(
    valid_telemetry: bool = True,
    boot_log: bool = False,
    corrupted_baud_rate: int | None = None,
) -> Callable[[MockSerialPort], None]:
    def generator(port: MockSerialPort) -> None:
        if corrupted_baud_rate and port.baudrate != corrupted_baud_rate:
            port.feed_bytes(b"\xcc\x33\x00\xff\xee\x11\r\n")
            return
        if boot_log:
            port.feed_line("rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)")
            port.feed_line("[I][main.cpp:42] Drone ESP32 Firmware initializing...")
        if valid_telemetry:
            payload = {
                "type": "telemetry",
                "attitude": {"roll": 1.25, "pitch": -0.75, "yaw": 92.4},
                "armed": True,
                "flight_mode": "STABILIZE",
                "pid": {
                    "roll": {"kp": 1.2, "ki": 0.08, "kd": 0.04, "setpoint": 0.0, "measured": 1.25, "output": -0.5}
                },
            }
            port.feed_line(json.dumps(payload))
    return generator


class VirtualSerialHub:
    """
    Central router that mocks serial.tools.list_ports.comports()
    and serial.Serial instantiation for pytest environments.
    """
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.ports: dict[str, MockListPortInfo] = {}
        self.device_generators: dict[str, Callable[[MockSerialPort], None]] = {}
        self.active_instances: list[MockSerialPort] = []

    def register_port(
        self,
        device: str,
        generator: Callable[[MockSerialPort], None] | None = None,
        vid: int = 0x1A86,
        pid: int = 0x7523,
        description: str = "USB-Serial (CH340)",
        serial_number: str | None = None,
    ) -> None:
        with self._lock:
            self.ports[device] = MockListPortInfo(
                device=device,
                description=description,
                vid=vid,
                pid=pid,
                serial_number=serial_number,
            )
            if generator:
                self.device_generators[device] = generator

    def register_gps(
        self,
        device: str,
        valid_sentences: bool = True,
        bad_checksum: bool = False,
        noise_prefix: bool = False,
        corrupted_baud_rate: int | None = None,
        vid: int = 0x1A86,
        pid: int = 0x7523,
        serial_number: str | None = None,
    ) -> None:
        self.register_port(
            device=device,
            generator=make_gps_generator(valid_sentences, bad_checksum, noise_prefix, corrupted_baud_rate),
            vid=vid,
            pid=pid,
            description="USB-Serial CH340 (GPS)",
            serial_number=serial_number,
        )

    def register_esp(
        self,
        device: str,
        valid_telemetry: bool = True,
        boot_log: bool = False,
        corrupted_baud_rate: int | None = None,
        vid: int = 0x1A86,
        pid: int = 0x7523,
        serial_number: str | None = None,
    ) -> None:
        self.register_port(
            device=device,
            generator=make_esp_generator(valid_telemetry, boot_log, corrupted_baud_rate),
            vid=vid,
            pid=pid,
            description="USB-Serial CH340 (ESP32)",
            serial_number=serial_number,
        )

    def register_silent(self, device: str) -> None:
        def silent_gen(port: MockSerialPort):
            pass
        self.register_port(device=device, generator=silent_gen)

    def register_modem(self, device: str) -> None:
        def modem_gen(port: MockSerialPort):
            port.feed_line("AT+CGMI")
            port.feed_line("OK")
        self.register_port(device=device, generator=modem_gen)

    def unregister_port(self, device: str) -> None:
        with self._lock:
            self.ports.pop(device, None)
            self.device_generators.pop(device, None)
            for inst in list(self.active_instances):
                if inst.port == device:
                    inst.disconnect_on_read = True
                    inst.disconnect_on_write = True

    def list_comports(self) -> list[MockListPortInfo]:
        with self._lock:
            return list(self.ports.values())

    def open_port(self, *args: Any, **kwargs: Any) -> MockSerialPort:
        with self._lock:
            port = kwargs.pop("port", args[0] if args else None)
            rem_args = args[1:] if args else ()
            baud = kwargs.pop("baudrate", rem_args[0] if rem_args else 9600)
            if port not in self.ports:
                raise serial.SerialException(f"Port {port} does not exist in VirtualSerialHub")
            instance = MockSerialPort(port=port, baudrate=baud, **kwargs)
            generator = self.device_generators.get(port)
            instance._generator = generator
            if generator:
                generator(instance)
            self.active_instances.append(instance)
            return instance


class ReferenceUsbPortCoordinator:
    """
    Specification-compliant UsbPortCoordinator per PROJECT.md interface contracts.
    Serves as an authoritative contract reference and fallback while backend/app/serial_io.py
    implementation is in progress by worker_impl_1.
    """
    def __init__(
        self,
        gps_target: str = "auto",
        esp_target: str = "auto",
        gps_baud: int = 38400,
        esp_baud: int = 115200,
        probe_timeout: float = 0.5,
    ) -> None:
        self._lock = threading.RLock()
        self.gps_target = gps_target
        self.esp_target = esp_target
        self.gps_baud = gps_baud
        self.esp_baud = esp_baud
        self.probe_timeout = probe_timeout
        self.assigned: dict[str, str | None] = {"gps": None, "esp": None}
        self.active_ports: set[str] = set()

    def get_device_for_role(self, role: str) -> str | None:
        with self._lock:
            if self.assigned.get(role):
                return self.assigned[role]
            self._scan_and_assign_unlocked()
            return self.assigned.get(role)

    # Aliases per survey recommendations
    get_port = get_device_for_role
    get_device = get_device_for_role

    def release_device_for_role(self, role: str, device: str) -> None:
        with self._lock:
            if self.assigned.get(role) == device:
                self.assigned[role] = None
            self.active_ports.discard(device)

    # Aliases
    release_port = release_device_for_role
    release_device = release_device_for_role

    def scan_and_assign(self) -> dict[str, str | None]:
        with self._lock:
            return self._scan_and_assign_unlocked()

    def _scan_and_assign_unlocked(self) -> dict[str, str | None]:
        try:
            available_ports = [p.device for p in serial.tools.list_ports.comports()]
        except Exception:
            available_ports = []

        # Pinned overrides
        if self.gps_target != "auto" and self.gps_target in available_ports:
            self.assigned["gps"] = self.gps_target
            self.active_ports.add(self.gps_target)

        if self.esp_target != "auto" and self.esp_target in available_ports:
            if self.esp_target != self.assigned.get("gps"):
                self.assigned["esp"] = self.esp_target
                self.active_ports.add(self.esp_target)

        unassigned_candidates = [
            p for p in available_ports
            if p not in self.active_ports
        ]

        for port_name in unassigned_candidates:
            if self.assigned.get("gps") and self.assigned.get("esp"):
                break
            classification = self.probe_port(port_name)
            if classification == "gps" and not self.assigned.get("gps"):
                self.assigned["gps"] = port_name
                self.active_ports.add(port_name)
            elif classification == "esp" and not self.assigned.get("esp"):
                self.assigned["esp"] = port_name
                self.active_ports.add(port_name)

        return dict(self.assigned)

    def probe_port(self, port_name: str) -> str:
        """
        Safely probes candidate port without asserting DTR/RTS.
        Returns 'gps', 'esp', or 'unknown'.
        """
        import pynmea2

        # Stage 1: Probe GPS at 38400 baud
        try:
            with serial.Serial(
                port_name,
                self.gps_baud,
                timeout=self.probe_timeout,
                dtr=False,
                rts=False,
                dsrdtr=False,
                rtscts=False,
            ) as port:
                port.reset_input_buffer()
                start = time.monotonic()
                while time.monotonic() - start < self.probe_timeout:
                    line = port.readline().decode("ascii", errors="replace").strip()
                    if line.startswith("$"):
                        try:
                            msg = pynmea2.parse(line, check=True)
                            if getattr(msg, "sentence_type", "") in ("GGA", "RMC", "GSA", "GSV", "VTG"):
                                return "gps"
                        except Exception:
                            pass
        except Exception:
            pass

        # Stage 2: Probe ESP at 115200 baud
        try:
            with serial.Serial(
                port_name,
                self.esp_baud,
                timeout=self.probe_timeout,
                dtr=False,
                rts=False,
                dsrdtr=False,
                rtscts=False,
            ) as port:
                port.reset_input_buffer()
                start = time.monotonic()
                while time.monotonic() - start < self.probe_timeout:
                    raw = port.readline().decode("utf-8", errors="replace").strip()
                    if not raw:
                        continue
                    if "rst:0x" in raw or "SPI_FAST_FLASH_BOOT" in raw or "Drone ESP32" in raw:
                        return "esp"
                    try:
                        payload = json.loads(raw)
                        if payload.get("type") in ("telemetry", "ack", "pong") or "attitude" in payload:
                            return "esp"
                    except Exception:
                        pass

                # Stage 2b: Active probe ping if passive is quiet
                port.write(b'{"type":"ping"}\n')
                port.flush()
                reply = port.readline().decode("utf-8", errors="replace").strip()
                if reply:
                    try:
                        p = json.loads(reply)
                        if p.get("type") in ("ack", "pong"):
                            return "esp"
                    except Exception:
                        pass
        except Exception:
            pass

        return "unknown"


# Register alias in sys.modules so imports like `import serial_test_harness` work seamlessly
sys.modules["serial_test_harness"] = sys.modules[__name__]


@pytest.fixture
def virtual_serial() -> Generator[VirtualSerialHub, None, None]:
    """Provides an isolated VirtualSerialHub with monkeypatched serial operations."""
    hub = VirtualSerialHub()

    def fake_comports() -> list[MockListPortInfo]:
        return hub.list_comports()

    def fake_serial_factory(*args: Any, **kwargs: Any) -> MockSerialPort:
        return hub.open_port(*args, **kwargs)

    with patch("serial.tools.list_ports.comports", side_effect=fake_comports), \
         patch("serial.Serial", side_effect=fake_serial_factory):
        yield hub


@pytest.fixture
def coordinator_factory():
    """
    Returns the UsbPortCoordinator class to test.
    Prefers backend.app.serial_io.UsbPortCoordinator when implemented by worker_impl_1;
    otherwise supplies ReferenceUsbPortCoordinator.
    """
    def _create(*args: Any, **kwargs: Any) -> Any:
        try:
            from app import serial_io
            if hasattr(serial_io, "UsbPortCoordinator"):
                return serial_io.UsbPortCoordinator(*args, **kwargs)
        except Exception:
            pass
        return ReferenceUsbPortCoordinator(*args, **kwargs)

    return _create
