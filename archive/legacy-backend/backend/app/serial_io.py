from __future__ import annotations

import asyncio
import glob
import json
import logging
import math
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4

import pynmea2
import serial
import serial.tools.list_ports

from .config import settings
from .models import AckFrame, Attitude, CommandFrame, GpsFix, PidAxis, TelemetryFrame

log = logging.getLogger(__name__)


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (ValueError, TypeError):
        return default


class TelemetryState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.frame = TelemetryFrame()
        self.raw_esp: deque[str] = deque(maxlen=200)
        self.acks: dict[str, AckFrame] = {}
        self.last_gps_monotonic = 0.0
        self.last_esp_monotonic = 0.0

    def snapshot(self) -> TelemetryFrame:
        with self._lock:
            frame = self.frame.model_copy(deep=True)
            now = time.monotonic()
            frame.gps_connected = now - self.last_gps_monotonic < settings.gps_stale_seconds
            frame.esp_connected = now - self.last_esp_monotonic < settings.gps_stale_seconds
            frame.gps.stale = not frame.gps_connected
            return frame

    def update_gps(self, fix: GpsFix) -> None:
        with self._lock:
            self.frame.gps = fix
            self.last_gps_monotonic = time.monotonic()

    def update_esp_line(self, line: str) -> None:
        with self._lock:
            self.raw_esp.append(line)
            try:
                payload = json.loads(line)
            except (json.JSONDecodeError, TypeError, ValueError):
                return
            if not isinstance(payload, dict):
                return
            self.last_esp_monotonic = time.monotonic()
            self.frame.esp_connected = True
            if payload.get("type") == "ack":
                try:
                    ack = AckFrame.model_validate(payload)
                except ValueError:
                    return
                self.acks[str(ack.command_id)] = ack
                while len(self.acks) > 200:
                    self.acks.pop(next(iter(self.acks)))
                return
            if payload.get("type") != "telemetry":
                return
            attitude = payload.get("attitude") if isinstance(payload.get("attitude"), dict) else {}
            self.frame.attitude = Attitude(
                roll=_safe_float(attitude.get("roll"), 0.0),
                pitch=_safe_float(attitude.get("pitch"), 0.0),
                yaw=_safe_float(attitude.get("yaw"), 0.0),
            )
            self.frame.armed = bool(payload.get("armed", False))
            self.frame.flight_mode = str(payload.get("flight_mode", "UNKNOWN"))[:32]
            pid_data = payload.get("pid") if isinstance(payload.get("pid"), dict) else {}
            for axis in ("roll", "pitch", "yaw"):
                if axis in pid_data and isinstance(pid_data[axis], dict):
                    try:
                        self.frame.pid[axis] = PidAxis.model_validate(pid_data[axis])
                    except (ValueError, TypeError):
                        pass

    def take_ack(self, command_id: str) -> AckFrame | None:
        with self._lock:
            return self.acks.pop(command_id, None)


state = TelemetryState()


def parse_nmea_line(line: str, previous: GpsFix | None = None) -> GpsFix | None:
    if not line.startswith("$"):
        return None
    try:
        message = pynmea2.parse(line, check=True)
    except (pynmea2.ParseError, ValueError):
        return None
    previous = previous or GpsFix()
    values = previous.model_dump()
    values.update(timestamp=datetime.now(timezone.utc), raw=line, stale=False)
    sentence = getattr(message, "sentence_type", "")
    if sentence == "GGA":
        quality = int(message.gps_qual or 0)
        values.update(
            latitude=float(message.latitude) if message.latitude else None,
            longitude=float(message.longitude) if message.longitude else None,
            altitude_m=float(message.altitude) if message.altitude else None,
            satellites=int(message.num_sats) if message.num_sats else None,
            hdop=float(message.horizontal_dil) if message.horizontal_dil else None,
            fix_quality=quality,
            valid=quality > 0 and bool(message.latitude) and bool(message.longitude),
        )
    elif sentence == "RMC":
        status = getattr(message, "status", "V")
        values.update(
            latitude=float(message.latitude) if message.latitude else values["latitude"],
            longitude=float(message.longitude) if message.longitude else values["longitude"],
            speed_mps=float(message.spd_over_grnd) * 0.514444 if message.spd_over_grnd else 0,
            course_deg=float(message.true_course) if message.true_course else None,
            valid=status == "A" and bool(message.latitude) and bool(message.longitude),
        )
    else:
        return None
    return GpsFix.model_validate(values)


def open_serial_port(device: str, baud: int, timeout: float = 1.0) -> serial.Serial:
    """Safely opens a serial port suppressing DTR/RTS to avoid resetting ESP32."""
    try:
        port = serial.Serial(
            device,
            baud,
            timeout=timeout,
            dtr=False,
            rts=False,
            dsrdtr=False,
            rtscts=False,
        )
        try:
            port.dtr = False
            port.rts = False
        except Exception:
            pass
        if hasattr(port, "_lock"):
            port._lock = threading.RLock()
        return port
    except (TypeError, ValueError):
        port = serial.Serial()
        port.port = device
        port.baudrate = baud
        port.timeout = timeout
        port.dsrdtr = False
        port.rtscts = False
        try:
            port.dtr = False
            port.rts = False
        except Exception:
            pass
        port.open()
        try:
            port.dtr = False
            port.rts = False
        except Exception:
            pass
        if hasattr(port, "_lock"):
            port._lock = threading.RLock()
        return port


def is_valid_nmea_checksum(sentence: str) -> bool:
    """Calculates XOR checksum between '$' and '*' and compares to hex checksum."""
    if not sentence.startswith("$") or "*" not in sentence:
        return False
    parts = sentence[1:].split("*", 1)
    if len(parts) != 2 or len(parts[1]) < 2:
        return False
    content, expected_hex = parts[0], parts[1][:2]
    calculated_xor = 0
    for char in content:
        calculated_xor ^= ord(char)
    try:
        return calculated_xor == int(expected_hex, 16)
    except ValueError:
        return False


class UsbPortCoordinator:
    """Coordinates USB serial port discovery, content-based probing, and exclusive leasing."""

    def __init__(
        self,
        gps_target: str | None = None,
        esp_target: str | None = None,
        gps_baud: int | None = None,
        esp_baud: int | None = None,
        probe_timeout: float | None = None,
    ) -> None:
        self._state_lock = threading.Lock()
        self._scan_lock = threading.Lock()
        self.gps_target = gps_target if gps_target is not None else settings.gps_device
        self.esp_target = esp_target if esp_target is not None else settings.esp_device
        self.gps_baud = gps_baud if gps_baud is not None else settings.gps_baud
        self.esp_baud = esp_baud if esp_baud is not None else settings.esp_baud
        self.probe_timeout = probe_timeout if probe_timeout is not None else getattr(settings, "serial_probe_timeout", 1.0)
        self.assigned: dict[str, str | None] = {"gps": None, "esp": None}
        self.active_ports: set[str] = set()

    def reset(self) -> None:
        """Reset all port assignments and leases."""
        with self._state_lock:
            self.assigned = {"gps": None, "esp": None}
            self.active_ports.clear()

    def find_candidate_ports(self) -> list[str]:
        """Discover candidate serial port paths across platforms."""
        ports: list[str] = []
        try:
            for p in serial.tools.list_ports.comports():
                dev = getattr(p, "device", None) or str(p)
                if dev:
                    try:
                        p_dev = Path(dev)
                        resolved = str(p_dev.resolve()) if p_dev.is_symlink() or (p_dev.is_absolute() and p_dev.exists()) else dev
                    except Exception:
                        resolved = dev
                    if resolved not in ports:
                        ports.append(resolved)
        except Exception:
            pass

        for pattern in ("/dev/ttyUSB*", "/dev/ttyACM*", "/dev/serial/by-path/*", "/dev/serial/by-id/*"):
            try:
                for path in sorted(glob.glob(pattern)):
                    try:
                        p_path = Path(path)
                        resolved = str(p_path.resolve()) if p_path.is_symlink() or (p_path.is_absolute() and p_path.exists()) else path
                    except Exception:
                        resolved = path
                    if resolved not in ports:
                        ports.append(resolved)
            except Exception:
                pass
        return ports

    def _probe_gps(self, device: str) -> bool:
        """Probes device at GPS baud rate for valid NMEA sentences with verified checksums."""
        port = None
        try:
            port = open_serial_port(device, self.gps_baud, timeout=min(self.probe_timeout, 0.4))
            deadline = time.monotonic() + min(self.probe_timeout, 0.8)
            bad_nmea_count = 0
            while time.monotonic() < deadline:
                raw = port.readline()
                if not raw:
                    break
                if isinstance(raw, bytes):
                    line = raw.decode("ascii", errors="replace").strip()
                else:
                    line = str(raw).strip()

                if line.startswith("$"):
                    try:
                        parsed = pynmea2.parse(line, check=True)
                        if parsed and getattr(parsed, "sentence_type", None) in (
                            "GGA", "RMC", "GSA", "GSV", "VTG", "GLL", "ZDA"
                        ):
                            return True
                    except Exception:
                        pass
                    bad_nmea_count += 1
                    if bad_nmea_count >= 2:
                        break
                elif line.startswith("{") or "telemetry" in line or line.startswith("rst:"):
                    # Fast exit: definitely not GPS
                    break
        except Exception as exc:
            log.debug("GPS probe failed on %s: %s", device, exc)
        finally:
            if port:
                try:
                    port.close()
                except Exception:
                    pass
        return False

    def _probe_esp(self, device: str) -> bool:
        """Probes device at ESP baud rate for JSON telemetry, acks, or bootloader strings."""
        port = None
        try:
            port = open_serial_port(device, self.esp_baud, timeout=min(self.probe_timeout, 0.4))
            deadline = time.monotonic() + min(self.probe_timeout, 0.8)
            saw_nmea = False
            while time.monotonic() < deadline:
                raw = port.readline()
                if not raw:
                    break
                if isinstance(raw, bytes):
                    line = raw.decode("utf-8", errors="replace").strip()
                else:
                    line = str(raw).strip()

                if line.startswith("{") and line.endswith("}"):
                    try:
                        payload = json.loads(line)
                        if isinstance(payload, dict):
                            msg_type = payload.get("type")
                            if msg_type in ("telemetry", "ack", "pong") or any(
                                k in payload for k in ("attitude", "pid", "armed", "command")
                            ):
                                return True
                    except Exception:
                        pass

                esp_signatures = ("rst:", "boot:", "configsip:", "SPIWP:", "[I][", "[E][", "[W][", "ESP-IDF", "ESP32", "Drone ESP32")
                if any(sig in line for sig in esp_signatures):
                    return True

                if line.startswith("$"):
                    # Fast exit: definitely GPS, not ESP
                    saw_nmea = True
                    break

            if saw_nmea:
                return False

            # Fallback active ping
            try:
                port.write(b'{"type":"ping"}\n')
                if hasattr(port, "flush"):
                    port.flush()
                ping_deadline = time.monotonic() + 0.3
                while time.monotonic() < ping_deadline:
                    raw = port.readline()
                    if not raw:
                        break
                    if isinstance(raw, bytes):
                        line = raw.decode("utf-8", errors="replace").strip()
                    else:
                        line = str(raw).strip()

                    if line.startswith("{") and line.endswith("}"):
                        try:
                            payload = json.loads(line)
                            if isinstance(payload, dict) and (
                                payload.get("type") in ("pong", "ack", "telemetry") or "command_id" in payload or "accepted" in payload
                            ):
                                return True
                        except Exception:
                            pass
                    if any(sig in line for sig in ("rst:", "boot:", "configsip:", "ESP-IDF", "ESP32", "pong")):
                        return True
            except Exception:
                pass
        except Exception as exc:
            log.debug("ESP probe failed on %s: %s", device, exc)
        finally:
            if port:
                try:
                    port.close()
                except Exception:
                    pass
        return False

    def probe_port(self, device: str) -> Literal["gps", "esp", "unknown"]:
        """Probe candidate port and classify as 'gps', 'esp', or 'unknown'."""
        if self._probe_gps(device):
            return "gps"
        if self._probe_esp(device):
            return "esp"
        return "unknown"

    def probe_device(self, device: str) -> Literal["gps", "esp", "unknown"]:
        """Alias for probe_port."""
        return self.probe_port(device)

    def scan_and_assign(self) -> dict[str, str]:
        """Scans unleased candidate ports, assigns roles, and returns mapping."""
        with self._scan_lock:
            gps_target = self.gps_target if self.gps_target != "auto" else settings.gps_device
            esp_target = self.esp_target if self.esp_target != "auto" else settings.esp_device

            with self._state_lock:
                if gps_target != "auto" and self.assigned["gps"] is None:
                    if Path(gps_target).exists() or gps_target.upper().startswith("COM"):
                        if gps_target not in self.active_ports:
                            self.assigned["gps"] = gps_target
                            self.active_ports.add(gps_target)

                if esp_target != "auto" and self.assigned["esp"] is None:
                    if Path(esp_target).exists() or esp_target.upper().startswith("COM"):
                        if esp_target not in self.active_ports:
                            self.assigned["esp"] = esp_target
                            self.active_ports.add(esp_target)

                if self.assigned["gps"] is not None and self.assigned["esp"] is not None:
                    return {k: v for k, v in self.assigned.items() if v is not None}

            candidates = self.find_candidate_ports()
            for candidate in candidates:
                with self._state_lock:
                    if candidate in self.active_ports or candidate in self.assigned.values():
                        continue
                    if self.assigned["gps"] is not None and self.assigned["esp"] is not None:
                        break

                role = self.probe_port(candidate)
                with self._state_lock:
                    if role in ("gps", "esp") and self.assigned[role] is None:
                        if candidate not in self.active_ports:
                            self.assigned[role] = candidate
                            self.active_ports.add(candidate)
                            log.info("UsbPortCoordinator assigned %s to %s", candidate, role.upper())

            with self._state_lock:
                return {k: v for k, v in self.assigned.items() if v is not None}

    def get_device_for_role(self, role: str) -> str | None:
        """Thread-safe retrieval of leased device path for role ('gps' or 'esp')."""
        with self._state_lock:
            dev = self.assigned.get(role)
            if dev is not None:
                return dev

        self.scan_and_assign()
        with self._state_lock:
            return self.assigned.get(role)

    def get_device(self, role: str) -> str | None:
        """Alias for get_device_for_role."""
        return self.get_device_for_role(role)

    def get_port(self, role: str) -> str | None:
        """Alias for get_device_for_role."""
        return self.get_device_for_role(role)

    def release_device_for_role(self, role: str, device: str | None = None) -> None:
        """Called on disconnect or SerialException to release lease."""
        with self._state_lock:
            current = self.assigned.get(role)
            if device is None or current == device:
                self.assigned[role] = None
                if current:
                    self.active_ports.discard(current)
            if device:
                self.active_ports.discard(device)
            log.info("UsbPortCoordinator released %s for role %s", device or current, role)

    def release_device(self, role: str, device: str | None = None) -> None:
        """Alias for release_device_for_role."""
        self.release_device_for_role(role, device)

    def release_port(self, role: str, device: str | None = None) -> None:
        """Alias for release_device_for_role."""
        self.release_device_for_role(role, device)


coordinator = UsbPortCoordinator()


def gps_device() -> str | None:
    return coordinator.get_device_for_role("gps")


def esp_device() -> str | None:
    return coordinator.get_device_for_role("esp")


class SerialWorker:
    def __init__(self, name: str, device_resolver: Callable[[], str | None], baud: int, line_handler: Callable[[str], None]):
        self.name = name
        self.device_resolver = device_resolver
        self.baud = baud
        self.line_handler = line_handler
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.port: serial.Serial | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run, name=f"serial-{self.name}", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        with self._lock:
            if self.port:
                try:
                    self.port.close()
                except Exception:
                    pass
        if self.thread:
            self.thread.join(timeout=2.0)

    def write_line(self, line: str) -> bool:
        with self._lock:
            if not self.port or not getattr(self.port, "is_open", False):
                return False
            try:
                self.port.write((line.rstrip() + "\n").encode())
                if hasattr(self.port, "flush"):
                    self.port.flush()
                return True
            except (serial.SerialException, OSError, AttributeError):
                return False

    def _run(self) -> None:
        current_device: str | None = None
        while not self.stop_event.is_set():
            device = self.device_resolver()
            if not device:
                self.stop_event.wait(timeout=2.0)
                continue
            current_device = device
            try:
                port = open_serial_port(device, self.baud, timeout=1.0)
                with self._lock:
                    self.port = port
                log.info("%s connected to %s", self.name, device)
                while not self.stop_event.is_set():
                    raw = port.readline()
                    if raw:
                        if isinstance(raw, bytes):
                            line = raw.decode("utf-8", errors="replace").strip()
                        else:
                            line = str(raw).strip()
                        try:
                            self.line_handler(line)
                        except Exception as exc:
                            log.warning("%s line_handler error on %r: %s", self.name, line, exc)
            # Closing a POSIX serial port while another thread is blocked in
            # readline can surface as TypeError inside pyserial (fd becomes
            # None). Treat it as the same expected reconnect/shutdown path.
            except (serial.SerialException, OSError, TypeError) as exc:
                log.warning("%s serial unavailable: %s", self.name, exc)
            finally:
                with self._lock:
                    if self.port:
                        try:
                            self.port.close()
                        except Exception:
                            pass
                    self.port = None
                if coordinator and current_device:
                    coordinator.release_device_for_role(self.name, current_device)
            self.stop_event.wait(timeout=2.0)


def _handle_gps(line: str) -> None:
    parsed = parse_nmea_line(line, state.snapshot().gps)
    if parsed:
        state.update_gps(parsed)


gps_worker = SerialWorker("gps", gps_device, settings.gps_baud, _handle_gps)
esp_worker = SerialWorker("esp", esp_device, settings.esp_baud, state.update_esp_line)


class CommandDispatcher:
    def __init__(self, worker: SerialWorker = esp_worker, telemetry_state: TelemetryState = state):
        self.worker = worker
        self.telemetry_state = telemetry_state

    async def land(self, reason: str) -> tuple[CommandFrame, AckFrame | None, int]:
        valid_reasons = {"GEOFENCE_BREACH", "GPS_LOST", "ADMIN"}
        safe_reason = reason if reason in valid_reasons else ("GEOFENCE_BREACH" if "GEOFENCE" in reason.upper() else ("GPS_LOST" if "GPS" in reason.upper() else "ADMIN"))
        frame = CommandFrame(id=uuid4(), command="LAND", reason=safe_reason)  # type: ignore[arg-type]
        encoded = frame.model_dump_json()
        for attempt in range(1, 4):
            if not self.worker.write_line(encoded):
                return frame, None, attempt
            deadline = asyncio.get_running_loop().time() + 0.5
            while asyncio.get_running_loop().time() < deadline:
                ack = self.telemetry_state.take_ack(str(frame.id))
                if ack is not None:
                    return frame, ack, attempt
                await asyncio.sleep(0.02)
        return frame, None, 3


command_dispatcher = CommandDispatcher()


async def simulated_telemetry() -> None:
    """Provides recognizable UI motion only when no ESP is connected."""
    phase = 0.0
    while True:
        await asyncio.sleep(0.2)
        if state.snapshot().esp_connected:
            continue
        phase += 0.08
        import math

        with state._lock:
            state.frame.attitude = Attitude(
                roll=math.sin(phase) * 4,
                pitch=math.cos(phase * 0.7) * 3,
                yaw=(phase * 8) % 360,
            )
            state.frame.flight_mode = "SIMULATOR"
            for offset, axis in enumerate(("roll", "pitch", "yaw")):
                measured = math.sin(phase + offset) * 2
                state.frame.pid[axis] = PidAxis(kp=1.2, ki=0.08, kd=0.04, setpoint=0, measured=measured, output=-measured * 1.2)
