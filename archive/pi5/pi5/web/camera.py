from __future__ import annotations

import os
import subprocess
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


class V4L2CameraAdapter:
    """Read-only device probe; frame capture is intentionally not implicit."""

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
        try:
            result = subprocess.run(
                [
                    "v4l2-ctl",
                    f"--device={self.device_path}",
                    "--stream-mmap",
                    "--stream-count=1",
                    "--stream-to=-",
                ],
                capture_output=True,
                check=False,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            self.last_error = (CameraState.FRAME_READ_FAILED, CameraErrorCode.FRAME_READ_FAILED, type(exc).__name__)
            return None
        if result.returncode != 0 or not result.stdout:
            self.last_error = (CameraState.FRAME_READ_FAILED, CameraErrorCode.FRAME_READ_FAILED, "v4l2 single-frame read failed")
            return None
        if len(result.stdout) > self.max_frame_bytes:
            self.last_error = (CameraState.FRAME_READ_FAILED, CameraErrorCode.FRAME_READ_FAILED, "frame exceeds bounded memory limit")
            return None
        self.sequence += 1
        return CameraFrame(self.sequence, "image/jpeg", result.stdout, _now())

    def disconnect_consumer(self) -> None:
        self.stop()
