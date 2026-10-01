"""Single owner of the ESP32 USB serial port on the Pi.

One background loop reads the newest telemetry frame and keeps the ESP's
link-alive heartbeat going with ``$PING``. Web routes read the cached sample
and send checked command lines through :meth:`EspLink.send`. Firmware flashing
pauses the link so esptool can own the port.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import threading
import time
from typing import Any, Callable

from .esp_command import ping
from .esp_usb import ReadOnlyEspUsbTelemetrySource, UsbSerialLineReader


class EspLinkError(Exception):
    pass


class EspLink:
    def __init__(self, reader: Any | None, *, clock: Callable[[], float] = time.monotonic, ping_interval: float = 2.0, stale_after: float = 2.0) -> None:
        self._reader = reader
        self._clock = clock
        self._ping_interval = ping_interval
        self._stale_after = stale_after
        self._lock = threading.RLock()
        self._paused = False
        self._source = ReadOnlyEspUsbTelemetrySource(read_line=self._read_raw) if reader is not None else ReadOnlyEspUsbTelemetrySource()
        self._latest: dict[str, object] | None = None
        self._latest_at: float | None = None
        self._last_ping: float | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.sent: deque[tuple[str, str]] = deque(maxlen=50)

    @classmethod
    def for_device(cls, device_path: str | None) -> "EspLink":
        return cls(UsbSerialLineReader(device_path, allow_commands=True) if device_path else None)

    def _read_raw(self, timeout: float) -> bytes:
        return self._reader.read_latest(timeout)

    def tick(self) -> None:
        """One read and, when due, one heartbeat. Never raises."""
        with self._lock:
            if self._reader is None or self._paused:
                return
            sample = self._source.read()
            device = sample.get("device") or {}
            if not (isinstance(device, dict) and device.get("error")):
                self._latest, self._latest_at = sample, self._clock()
            now = self._clock()
            if self._last_ping is None or now - self._last_ping >= self._ping_interval:
                self._last_ping = now
                try:
                    self._write(ping())
                except EspLinkError:
                    pass

    def read(self) -> dict[str, object]:
        """Newest telemetry sample, or an UNAVAILABLE sample when it is stale."""
        with self._lock:
            if self._reader is None:
                return self._source._unavailable(datetime.now(timezone.utc), "ESP_USB_NOT_CONFIGURED")
            if self._latest is not None and self._latest_at is not None and self._clock() - self._latest_at <= self._stale_after:
                return self._latest
            return self._source._unavailable(datetime.now(timezone.utc), "ESP_FLASH_IN_PROGRESS" if self._paused else "ESP_USB_TIMEOUT")

    def arm_state(self) -> str | None:
        device = self.read().get("device") or {}
        flight = device.get("flight") if isinstance(device, dict) else None
        return flight.get("arm_state") if isinstance(flight, dict) else None

    def _write(self, line: bytes) -> None:
        try:
            self._reader.write_line(line)
        except Exception as exc:
            raise EspLinkError("ESP_WRITE_FAILED") from exc
        self.sent.append((datetime.now(timezone.utc).isoformat(), line.decode("ascii", "replace").strip()))

    def send(self, line: bytes) -> None:
        with self._lock:
            if self._reader is None:
                raise EspLinkError("ESP_NOT_CONNECTED")
            if self._paused:
                raise EspLinkError("ESP_LINK_PAUSED")
            self._write(line)

    def pause(self) -> None:
        with self._lock:
            self._paused = True
            self._latest = None
            if self._reader is not None:
                self._reader.close()

    def resume(self) -> None:
        with self._lock:
            self._paused = False
            self._last_ping = None

    def start(self, interval: float = 0.2) -> None:
        if self._thread is not None:
            return

        def loop() -> None:
            while not self._stop.wait(interval):
                self.tick()

        self._thread = threading.Thread(target=loop, name="esp-link", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        with self._lock:
            if self._reader is not None:
                self._reader.close()
