"""ESP32-over-USB telemetry frames and the serial line reader.

The ESP32 is the sensor owner. The Pi parses newline-delimited JSON frames
from an explicitly configured USB serial device. The reader can also write
one checked command line (see ``esp_command``) when it is opened with
``allow_commands=True``; there is no ARM, DISARM or motor command.
"""

from __future__ import annotations

import json
import math
import os
import select
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

try:
    import termios
except ImportError:  # pragma: no cover - the real adapter runs on Linux Pi only
    termios = None  # type: ignore[assignment]

TermiosError = getattr(termios, "error", OSError)

from ..web.models import FixState, TelemetrySample

ESP_USB_SCHEMA = "scope05.esp32.usb.v1"
ESP_USB_BAUDRATE = 115200
MAX_FRAME_BYTES = 16 * 1024
ALLOWED_DEVICE_PREFIXES = (
    "/dev/ttyUSB",
    "/dev/ttyACM",
    "/dev/serial/by-id/usb-Silicon_Labs_CP210",
)


class EspUsbFrameError(ValueError):
    """Raised when a received frame is not a bounded valid ESP frame."""


def _number(value: Any, *, name: str, minimum: float | None = None, maximum: float | None = None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise EspUsbFrameError(f"{name} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum or maximum is not None and result > maximum:
        raise EspUsbFrameError(f"{name} is outside the allowed range")
    return result


def _object(value: Any, *, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise EspUsbFrameError(f"{name} must be an object")
    return value


@dataclass(frozen=True)
class EspUsbFrame:
    sequence: int
    captured_at: datetime
    roll_deg: float | None
    pitch_deg: float | None
    yaw_deg: float | None
    altitude_m: float | None
    vertical_speed_mps: float | None
    battery_pct: float | None
    battery_voltage_v: float | None
    temperature_c: float | None
    sbus_signal_ok: bool | None
    sbus_channels: tuple[int, ...]
    gnss_fix_state: str | None
    latitude: float | None
    longitude: float | None
    gnss_altitude_m: float | None
    flight_status: dict[str, str]
    pid: dict[str, dict[str, float]]
    uptime_ms: int | None = None
    flight_extra: dict[str, Any] | None = None
    link: dict[str, Any] | None = None
    gnss_satellites: int | None = None

    def device_data(self) -> dict[str, Any]:
        return {
            "source": "ESP32_USB_SERIAL",
            "schema_version": ESP_USB_SCHEMA,
            "transport": {"baudrate": ESP_USB_BAUDRATE, "device": "USB_SERIAL_READ_ONLY"},
            "orientation": {"roll_deg": self.roll_deg, "pitch_deg": self.pitch_deg, "yaw_deg": self.yaw_deg},
            "barometer": {"altitude_m": self.altitude_m, "vertical_speed_mps": self.vertical_speed_mps},
            "power": {"battery_pct": self.battery_pct, "voltage_v": self.battery_voltage_v},
            "temperature_c": self.temperature_c,
            "sbus": {"signal_ok": self.sbus_signal_ok, "channels": list(self.sbus_channels)},
            "gnss": {
                "fix_state": self.gnss_fix_state,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "altitude_m": self.gnss_altitude_m,
                "satellites": self.gnss_satellites,
            },
            "flight": {**(self.flight_extra or {}), **self.flight_status},
            "pid": self.pid,
            "link": self.link or {},
            "uptime_ms": self.uptime_ms,
        }


def parse_esp_frame(line: str | bytes, *, capture_timestamp: datetime | None = None) -> EspUsbFrame:
    """Parse one bounded JSONL frame emitted by the ESP32 firmware."""

    if isinstance(line, bytes):
        if len(line) > MAX_FRAME_BYTES:
            raise EspUsbFrameError("frame is too large")
        try:
            text = line.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise EspUsbFrameError("frame is not UTF-8") from exc
    elif isinstance(line, str):
        if len(line.encode("utf-8")) > MAX_FRAME_BYTES:
            raise EspUsbFrameError("frame is too large")
        text = line.strip()
    else:
        raise EspUsbFrameError("frame must be text or bytes")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EspUsbFrameError("frame is not valid JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != ESP_USB_SCHEMA:
        raise EspUsbFrameError("unsupported ESP frame schema")
    sequence = payload.get("seq")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise EspUsbFrameError("seq must be a non-negative integer")
    imu = _object(payload.get("imu"), name="imu")
    baro = _object(payload.get("baro"), name="baro")
    power = _object(payload.get("power"), name="power")
    sbus = _object(payload.get("sbus"), name="sbus")
    gnss = _object(payload.get("gnss"), name="gnss")
    flight = _object(payload.get("flight"), name="flight")
    pid_payload = _object(payload.get("pid"), name="pid")
    channels = sbus.get("channels", [])
    if not isinstance(channels, list) or len(channels) > 16 or any(isinstance(item, bool) or not isinstance(item, int) or not 0 <= item <= 2047 for item in channels):
        raise EspUsbFrameError("sbus.channels must contain at most 16 values in 0..2047")
    signal_ok = sbus.get("signal_ok")
    if signal_ok is not None and not isinstance(signal_ok, bool):
        raise EspUsbFrameError("sbus.signal_ok must be boolean")
    fix_state = gnss.get("fix_state")
    if fix_state is not None and fix_state not in {"VALID_FIX", "NO_FIX", "STALE", "UNAVAILABLE"}:
        raise EspUsbFrameError("unsupported gnss.fix_state")
    latitude = _number(gnss.get("latitude"), name="gnss.latitude", minimum=-90, maximum=90)
    longitude = _number(gnss.get("longitude"), name="gnss.longitude", minimum=-180, maximum=180)
    if (latitude is None) != (longitude is None):
        raise EspUsbFrameError("latitude and longitude must be provided together")
    arm_state = flight.get("arm_state")
    mode = flight.get("mode")
    if arm_state is not None and arm_state not in {"ARMED", "DISARMED", "BLOCKED", "UNKNOWN"}:
        raise EspUsbFrameError("unsupported flight.arm_state")
    if mode is not None and (not isinstance(mode, str) or len(mode) > 32):
        raise EspUsbFrameError("flight.mode must be a short string")
    pid: dict[str, dict[str, float]] = {}
    for axis, values in pid_payload.items():
        if not isinstance(axis, str) or len(axis) > 16:
            raise EspUsbFrameError("pid axis name is invalid")
        axis_values = _object(values, name=f"pid.{axis}")
        parsed_values: dict[str, float] = {}
        for key in ("kp", "ki", "kd"):
            value = _number(axis_values.get(key), name=f"pid.{axis}.{key}", minimum=0, maximum=10000)
            if value is not None:
                parsed_values[key] = value
        pid[axis] = parsed_values
    uptime = payload.get("uptime_ms")
    if uptime is not None and (isinstance(uptime, bool) or not isinstance(uptime, int) or uptime < 0):
        raise EspUsbFrameError("uptime_ms must be a non-negative integer")
    flight_extra: dict[str, Any] = {}
    for key in ("authorization", "auth_ref", "arm_block_reason"):
        value = flight.get(key)
        if isinstance(value, str) and len(value) <= 64:
            flight_extra[key] = value
    for key in ("auth_remaining_s", "max_altitude_m", "throttle_us"):
        value = flight.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
            flight_extra[key] = value
    if isinstance(flight.get("altitude_limited"), bool):
        flight_extra["altitude_limited"] = flight["altitude_limited"]
    link_payload = _object(payload.get("link"), name="link")
    link = {k: v for k, v in link_payload.items() if k in {"last_cmd", "last_result", "cmd_count", "pi_heartbeat_age_ms"} and isinstance(v, (str, int)) and not isinstance(v, bool) and len(str(v)) <= 32}
    if isinstance(link_payload.get("pi_alive"), bool):
        link["pi_alive"] = link_payload["pi_alive"]
    satellites = gnss.get("satellites")
    if isinstance(satellites, bool) or not isinstance(satellites, int) or not 0 <= satellites <= 99:
        satellites = None
    return EspUsbFrame(
        uptime_ms=uptime,
        flight_extra=flight_extra,
        link=link,
        gnss_satellites=satellites,
        sequence=sequence,
        captured_at=capture_timestamp or datetime.now(timezone.utc),
        roll_deg=_number(imu.get("roll_deg"), name="imu.roll_deg", minimum=-360, maximum=360),
        pitch_deg=_number(imu.get("pitch_deg"), name="imu.pitch_deg", minimum=-360, maximum=360),
        yaw_deg=_number(imu.get("yaw_deg"), name="imu.yaw_deg", minimum=-360, maximum=360),
        altitude_m=_number(baro.get("altitude_m"), name="baro.altitude_m", minimum=-1000, maximum=100000),
        vertical_speed_mps=_number(baro.get("vertical_speed_mps"), name="baro.vertical_speed_mps", minimum=-1000, maximum=1000),
        battery_pct=_number(power.get("battery_pct"), name="power.battery_pct", minimum=0, maximum=100),
        battery_voltage_v=_number(power.get("voltage_v"), name="power.voltage_v", minimum=0, maximum=100),
        temperature_c=_number(payload.get("temperature_c", baro.get("temperature_c")), name="temperature_c", minimum=-100, maximum=200),
        sbus_signal_ok=signal_ok,
        sbus_channels=tuple(channels),
        gnss_fix_state=fix_state,
        latitude=latitude,
        longitude=longitude,
        gnss_altitude_m=_number(gnss.get("altitude_m"), name="gnss.altitude_m", minimum=-1000, maximum=100000),
        flight_status={
            key: value for key, value in (("arm_state", arm_state), ("mode", mode)) if isinstance(value, str)
        },
        pid=pid,
    )


class UsbSerialLineReader:
    """Linux USB-serial line reader that only calls ``os.read``."""

    def __init__(self, device_path: str, *, baudrate: int = ESP_USB_BAUDRATE, max_line_bytes: int = MAX_FRAME_BYTES, allow_commands: bool = False) -> None:
        if not device_path.startswith(ALLOWED_DEVICE_PREFIXES):
            raise ValueError("ESP USB device must be an explicit ttyUSB/ttyACM or CP210x by-id path")
        if baudrate != ESP_USB_BAUDRATE:
            raise ValueError("ESP USB telemetry baudrate must be 115200")
        self.device_path = device_path
        self.baudrate = baudrate
        self.max_line_bytes = max_line_bytes
        self._fd: int | None = None
        self._buffer = bytearray()
        # Mac dinh chi doc. allow_commands=True mo O_RDWR tren CUNG 1 fd de gui lenh
        # $AUTH/$PID/$MAXALT/$PING (khong mo fd thu hai -> tranh dao DTR/RTS reset ESP).
        self.allow_commands = allow_commands

    def _open(self) -> None:
        if self._fd is not None:
            return
        if termios is None:
            raise OSError("USB serial reader requires a POSIX Pi runtime")
        mode = os.O_RDWR if self.allow_commands else os.O_RDONLY
        fd = os.open(self.device_path, mode | os.O_NOCTTY | os.O_NONBLOCK)
        attrs = termios.tcgetattr(fd)
        attrs[4] = termios.B115200
        attrs[5] = termios.B115200
        attrs[3] &= ~(termios.ECHO | termios.ICANON | termios.ISIG)
        attrs[0] &= ~(termios.IXON | termios.IXOFF | termios.IXANY)
        attrs[2] |= termios.CLOCAL | termios.CREAD
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        self._fd = fd

    def read(self, timeout: float) -> bytes:
        if timeout < 0 or timeout > 30:
            raise ValueError("timeout must be within 0..30 seconds")
        self._open()
        assert self._fd is not None
        deadline = time.monotonic() + timeout
        while time.monotonic() <= deadline:
            newline = self._buffer.find(b"\n")
            if newline >= 0:
                line = bytes(self._buffer[:newline + 1])
                del self._buffer[:newline + 1]
                return line
            remaining = max(0.0, deadline - time.monotonic())
            ready, _, _ = select.select([self._fd], [], [], remaining)
            if not ready:
                break
            chunk = os.read(self._fd, min(4096, self.max_line_bytes + 1))
            if not chunk:
                break
            self._buffer.extend(chunk)
            if len(self._buffer) > self.max_line_bytes:
                self._buffer.clear()
                raise EspUsbFrameError("USB serial line is too large")
        return b""

    def read_latest(self, timeout: float) -> bytes:
        """Doc het du lieu dang cho va tra ve dong day du MOI NHAT (tranh tre khi Pi poll cham)."""
        line = self.read(timeout)
        while line:
            newer = self.read(0)
            if not newer:
                break
            line = newer
        return line

    def write_line(self, data: bytes) -> None:
        if not self.allow_commands:
            raise PermissionError("ESP USB reader is read-only; command channel is disabled")
        if not data.endswith(b"\n") or len(data) > 128:
            raise ValueError("command must be one newline-terminated line <= 128 bytes")
        self._open()
        assert self._fd is not None
        view = memoryview(data)
        deadline = time.monotonic() + 1.0
        while view:
            if time.monotonic() > deadline:
                raise TimeoutError("ESP USB write timed out")
            _, ready, _ = select.select([], [self._fd], [], 0.2)
            if ready:
                written = os.write(self._fd, view)
                view = view[written:]

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
            self._buffer.clear()


class ReadOnlyEspUsbTelemetrySource:
    """Pi web adapter for an injected or explicitly configured USB reader."""

    def __init__(self, read_line: Callable[[float], str | bytes | None] | None = None, *, device_path: str | None = None) -> None:
        if read_line is not None and device_path is not None:
            raise ValueError("provide read_line or device_path, not both")
        self.device_path = device_path
        self._reader = read_line or (UsbSerialLineReader(device_path) if device_path else None)
        self._sequence: int | None = None
        self._uptime: int | None = None
        self.dropped_frames = 0
        self.restarts = 0

    def read(self) -> dict[str, object]:
        now = datetime.now(timezone.utc)
        if self._reader is None:
            return self._unavailable(now, "ESP_USB_NOT_CONFIGURED")
        try:
            raw = self._reader(0.25) if callable(self._reader) else self._reader.read_latest(0.25)
            if not raw:
                return self._unavailable(now, "ESP_USB_TIMEOUT")
            frame = parse_esp_frame(raw, capture_timestamp=now)
            if self._sequence is not None:
                restarted = (
                    frame.uptime_ms is not None and self._uptime is not None and frame.uptime_ms < self._uptime
                )
                if restarted:
                    self.restarts += 1
                elif frame.sequence <= self._sequence:
                    return self._unavailable(now, "ESP_USB_SEQUENCE_REPLAY")
                elif frame.sequence != self._sequence + 1:
                    # Pi chi lay frame moi nhat -> bo qua frame cu la binh thuong; dem lai de theo doi.
                    self.dropped_frames += frame.sequence - self._sequence - 1
            self._sequence = frame.sequence
            self._uptime = frame.uptime_ms
            fix = {"VALID_FIX": FixState.FIX, "NO_FIX": FixState.NO_FIX, "STALE": FixState.STALE}.get(frame.gnss_fix_state, FixState.UNAVAILABLE)
            return TelemetrySample(
                schema_version=ESP_USB_SCHEMA,
                source="ESP32_USB_SERIAL",
                timestamp=frame.captured_at,
                sequence=frame.sequence,
                stale=fix in {FixState.STALE, FixState.UNAVAILABLE},
                fix_state=fix,
                latitude=frame.latitude,
                longitude=frame.longitude,
                altitude_m=frame.gnss_altitude_m or frame.altitude_m,
                heading_deg=frame.yaw_deg,
                pitch_deg=frame.pitch_deg,
                roll_deg=frame.roll_deg,
                device_data={**frame.device_data(), "dropped_frames": self.dropped_frames, "esp_restarts": self.restarts},
            ).as_dict()
        except EspUsbFrameError as exc:
            return self._unavailable(now, str(exc), invalid=True)
        except (OSError, TermiosError):
            return self._unavailable(now, "ESP_USB_READ_FAILED")
        except Exception:
            return self._unavailable(now, "ESP_USB_READ_FAILED")

    def _unavailable(self, timestamp: datetime, error: str, *, invalid: bool = False) -> dict[str, object]:
        return TelemetrySample(
            schema_version=ESP_USB_SCHEMA,
            source="ESP32_USB_SERIAL",
            timestamp=timestamp,
            sequence=self._sequence or 0,
            stale=True,
            fix_state=FixState.INVALID if invalid else FixState.UNAVAILABLE,
            device_data={
                "source": "ESP32_USB_SERIAL",
                "schema_version": ESP_USB_SCHEMA,
                "transport": {"device": self.device_path or "NOT_CONFIGURED", "baudrate": ESP_USB_BAUDRATE, "read_only": True},
                "error": error,
            },
        ).as_dict()

    def close(self) -> None:
        close = getattr(self._reader, "close", None)
        if close is not None:
            close()
