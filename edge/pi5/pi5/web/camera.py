from __future__ import annotations

import os
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Protocol

from .models import CameraErrorCode, CameraFrame, CameraState, CameraStatus


class CameraAdapter(Protocol):
    def status(self) -> CameraStatus: ...
    def start(self) -> CameraStatus: ...
    def stop(self) -> None: ...
    def read_frame(self) -> CameraFrame | None: ...
    def disconnect_consumer(self) -> None: ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MockCameraAdapter:
    def __init__(self, *, device_path: str = "/dev/video0", queue_size: int = 2) -> None:
        self.device_path = device_path
        self.queue: deque[CameraFrame] = deque(maxlen=queue_size)
        self.state = CameraState.AVAILABLE
        self.error_code: CameraErrorCode | None = None
        self.detail: str | None = None
        self.sequence = 0
        self.running = False
        self.consumer_count = 0
        self.delay_seconds = 0.0

    def set_state(self, state: CameraState, error_code: CameraErrorCode | None = None, detail: str | None = None) -> None:
        self.state, self.error_code, self.detail = state, error_code, detail
        if state != CameraState.AVAILABLE:
            self.queue.clear()

    def produce(self, payload: bytes | None, *, content_type: str = "image/jpeg") -> None:
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        if not payload:
            self.set_state(CameraState.FRAME_READ_FAILED, CameraErrorCode.EMPTY_FRAME, "empty frame")
            return
        self.sequence += 1
        self.queue.append(CameraFrame(self.sequence, content_type, payload, _now()))
        self.state = CameraState.AVAILABLE
        self.error_code = None
        self.detail = None

    def status(self) -> CameraStatus:
        return CameraStatus(self.state, self.device_path, "MOCK", self.error_code, self.detail, len(self.queue), _now())

    def start(self) -> CameraStatus:
        self.running = True
        self.consumer_count += 1
        return self.status()

    def stop(self) -> None:
        self.running = False
        self.consumer_count = 0
        self.queue.clear()

    def read_frame(self) -> CameraFrame | None:
        if not self.running or self.state != CameraState.AVAILABLE:
            return None
        return self.queue.popleft() if self.queue else None

    def disconnect_consumer(self) -> None:
        self.consumer_count = max(0, self.consumer_count - 1)
        if self.consumer_count == 0:
            self.stop()


MAX_PARTIAL_FRAME = 4 * 1024 * 1024


def split_jpeg_frames(buffer: bytearray) -> list[bytes]:
    """Remove and return every complete JPEG (SOI..EOI) from ``buffer``."""
    frames: list[bytes] = []
    while True:
        start = buffer.find(b"\xff\xd8")
        if start < 0:
            # Keep a trailing 0xFF: it may be the first half of the next SOI.
            del buffer[: len(buffer) - 1 if buffer.endswith(b"\xff") else len(buffer)]
            return frames
        if start:
            del buffer[:start]
        end = buffer.find(b"\xff\xd9", 2)
        if end < 0:
            if len(buffer) > MAX_PARTIAL_FRAME:
                del buffer[:]
            return frames
        frames.append(bytes(buffer[: end + 2]))
        del buffer[: end + 2]


class MjpegStreamer:
    """One shared ``v4l2-ctl`` capture process; consumers read the newest frame."""

    def __init__(self, device_path: str, *, popen=subprocess.Popen, width: int = 1280, height: int = 720, idle_seconds: float = 10.0) -> None:
        self.device_path = device_path
        self._popen = popen
        self._size = (width, height)
        self._idle_seconds = idle_seconds
        self._condition = threading.Condition()
        self._frame: bytes | None = None
        self._sequence = 0
        self._process = None
        self._thread: threading.Thread | None = None
        self._last_consumer = 0.0

    def _capture(self) -> None:
        buffer = bytearray()
        process = self._process
        try:
            while process is not None and process.poll() is None:
                chunk = process.stdout.read1(65536) if hasattr(process.stdout, "read1") else process.stdout.read(65536)
                if not chunk:
                    break
                buffer.extend(chunk)
                frames = split_jpeg_frames(buffer)
                if frames:
                    with self._condition:
                        self._frame = frames[-1]
                        self._sequence += 1
                        self._condition.notify_all()
                if time.monotonic() - self._last_consumer > self._idle_seconds:
                    break
        finally:
            self.stop()

    def start(self) -> None:
        with self._condition:
            self._last_consumer = time.monotonic()
            if self._process is not None:
                return
            width, height = self._size
            self._process = self._popen(
                ["v4l2-ctl", f"--device={self.device_path}", f"--set-fmt-video=width={width},height={height},pixelformat=MJPG", "--stream-mmap", "--stream-count=0", "--stream-to=-"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            self._thread = threading.Thread(target=self._capture, name="camera-mjpeg", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._condition:
            process, self._process = self._process, None
            self._frame = None
            self._condition.notify_all()
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=2)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

    def frames(self, *, timeout: float = 5.0):
        """Yield new frames until the capture stops or stalls."""
        try:
            self.start()
        except OSError:
            return
        seen = 0
        while True:
            with self._condition:
                self._last_consumer = time.monotonic()
                if self._sequence == seen and not self._condition.wait(timeout):
                    return
                if self._process is None or self._frame is None:
                    return
                seen, frame = self._sequence, self._frame
            yield frame

    def latest(self, *, timeout: float = 5.0) -> bytes | None:
        return next(self.frames(timeout=timeout), None)


class V4L2CameraAdapter:
    """USB webcam through v4l2-ctl: one shared MJPEG capture for every viewer."""

    def __init__(self, device_path: str = "/dev/video0", *, max_frame_bytes: int = 8 * 1024 * 1024) -> None:
        if device_path == "/dev/video1":
            raise ValueError("/dev/video1 is reserved as the inventory metadata node")
        if not device_path.startswith("/dev/video"):
            raise ValueError("camera device path must be an explicit /dev/videoN path")
        self.device_path = device_path
        self.max_frame_bytes = max_frame_bytes
        self.running = False
        self.sequence = 0
        self.last_error: tuple[CameraState, CameraErrorCode, str] | None = None
        self.streamer = MjpegStreamer(device_path)

    def mjpeg_frames(self):
        return self.streamer.frames()

    def status(self) -> CameraStatus:
        if not os.path.exists(self.device_path):
            return CameraStatus(CameraState.UNAVAILABLE, self.device_path, "V4L2", CameraErrorCode.DEVICE_UNAVAILABLE, "device path is absent", observed_at=_now())
        if not os.access(self.device_path, os.R_OK):
            return CameraStatus(CameraState.PERMISSION_DENIED, self.device_path, "V4L2", CameraErrorCode.PERMISSION_DENIED, "read permission denied", observed_at=_now())
        return CameraStatus(CameraState.AVAILABLE, self.device_path, "V4L2", observed_at=_now())

    def start(self) -> CameraStatus:
        status = self.status()
        self.running = status.state == CameraState.AVAILABLE
        self.last_error = None
        return status

    def stop(self) -> None:
        self.running = False

    def read_frame(self) -> CameraFrame | None:
        if not self.running:
            return None
        payload = self.streamer.latest()
        if not payload:
            self.last_error = (CameraState.FRAME_READ_FAILED, CameraErrorCode.FRAME_READ_FAILED, "no frame from the USB camera")
            return None
        if len(payload) > self.max_frame_bytes:
            self.last_error = (CameraState.FRAME_READ_FAILED, CameraErrorCode.FRAME_READ_FAILED, "frame exceeds bounded memory limit")
            return None
        self.sequence += 1
        return CameraFrame(self.sequence, "image/jpeg", payload, _now())

    def disconnect_consumer(self) -> None:
        self.stop()
