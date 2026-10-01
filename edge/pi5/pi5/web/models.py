from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PiRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class CameraState(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    BUSY = "BUSY"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    OPEN_FAILED = "OPEN_FAILED"
    FRAME_READ_FAILED = "FRAME_READ_FAILED"


class CameraErrorCode(str, Enum):
    DEVICE_UNAVAILABLE = "DEVICE_UNAVAILABLE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    DEVICE_BUSY = "DEVICE_BUSY"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    OPEN_FAILED = "OPEN_FAILED"
    FRAME_READ_FAILED = "FRAME_READ_FAILED"
    EMPTY_FRAME = "EMPTY_FRAME"


class CacheState(str, Enum):
    AVAILABLE = "AVAILABLE"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    CORRUPT = "CORRUPT"


class FixState(str, Enum):
    FIX = "FIX"
    NO_FIX = "NO_FIX"
    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"
    INVALID = "INVALID"


@dataclass(frozen=True)
class CameraStatus:
    state: CameraState
    device_path: str
    source: str
    error_code: CameraErrorCode | None = None
    detail: str | None = None
    queue_depth: int = 0
    observed_at: datetime = field(default_factory=utcnow)

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "device_path": self.device_path,
            "source": self.source,
            "error_code": self.error_code.value if self.error_code else None,
            "detail": self.detail,
            "queue_depth": self.queue_depth,
            "observed_at": self.observed_at.astimezone(timezone.utc).isoformat(),
        }


@dataclass(frozen=True)
class CameraFrame:
    sequence: int
    content_type: str
    payload: bytes
    captured_at: datetime

    def metadata(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "content_type": self.content_type,
            "size_bytes": len(self.payload),
            "captured_at": self.captured_at.astimezone(timezone.utc).isoformat(),
        }


@dataclass(frozen=True)
class CacheProvenance:
    source: str
    source_type: str
    fetched_at: datetime | None
    generated_at: datetime | None
    cache_version: str
    stale_after: datetime | None
    license: str
    is_stale: bool = False

    def as_dict(self) -> dict[str, Any]:
        def iso(value: datetime | None) -> str | None:
            return value.astimezone(timezone.utc).isoformat() if value else None

        return {
            "source": self.source,
            "source_type": self.source_type,
            "fetched_at": iso(self.fetched_at),
            "generated_at": iso(self.generated_at),
            "cache_version": self.cache_version,
            "stale_after": iso(self.stale_after),
            "license": self.license,
            "is_stale": self.is_stale,
        }


@dataclass(frozen=True)
class TelemetrySample:
    schema_version: str
    source: str
    timestamp: datetime
    sequence: int
    stale: bool
    fix_state: FixState
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None
    heading_deg: float | None = None
    pitch_deg: float | None = None
    roll_deg: float | None = None
    gnss_baudrate: int | None = None
    gnss_rx_pin: int | None = None
    gnss_tx_pin: int | None = None
    device_data: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source": self.source,
            "timestamp": self.timestamp.astimezone(timezone.utc).isoformat(),
            "sequence": self.sequence,
            "stale": self.stale,
            "fix_state": self.fix_state.value,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude_m": self.altitude_m,
            "heading_deg": self.heading_deg,
            "pitch_deg": self.pitch_deg,
            "roll_deg": self.roll_deg,
            "gnss": {
                "baudrate": self.gnss_baudrate,
                "rx_pin": self.gnss_rx_pin,
                "tx_pin": self.gnss_tx_pin,
            },
            "device": self.device_data,
        }


def envelope(data: Any = None, error: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "scope04.pi-web.v1",
        "data": data,
        "error": error,
        "observed_at": utcnow().isoformat(),
    }
