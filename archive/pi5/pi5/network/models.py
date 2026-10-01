from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SignalState(str, Enum):
    UNKNOWN = "UNKNOWN"
    UP = "UP"
    DOWN = "DOWN"


class AccessPointState(str, Enum):
    UP = "AP_UP"
    DEGRADED = "AP_DEGRADED"


class StationState(str, Enum):
    DISCONNECTED = "STA_DISCONNECTED"
    CONNECTING = "STA_CONNECTING"
    CONNECTED = "STA_CONNECTED"
    FAILED = "STA_FAILED"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("observed_at must include a timezone")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class InterfaceIdentity:
    name: str
    purpose: str
    verified: bool = False
    physical_path: str | None = None

    def __post_init__(self) -> None:
        if self.purpose not in {"onboard_ap", "usb_sta"}:
            raise ValueError("interface purpose must be onboard_ap or usb_sta")
        if not self.name or len(self.name) > 32 or any(char.isspace() for char in self.name):
            raise ValueError("interface name is invalid")


@dataclass(frozen=True)
class ReachabilitySignal:
    state: SignalState
    observed_at: datetime
    source: str
    stale: bool = False
    latency_ms: int | None = None
    timeout_ms: int | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", ensure_utc(self.observed_at))
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("latency_ms must not be negative")
        if self.timeout_ms is not None and self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "observed_at": self.observed_at.isoformat(),
            "source": self.source,
            "stale": self.stale,
            "latency_ms": self.latency_ms,
            "timeout_ms": self.timeout_ms,
            "error_code": self.error_code,
        }


@dataclass(frozen=True)
class ProfileDraft:
    purpose: str
    interface_name: str
    ssid: str
    credential_present: bool
    version: int

    def as_redacted(self) -> dict[str, Any]:
        return {
            "purpose": self.purpose,
            "interface_name": self.interface_name,
            "ssid": self.ssid,
            "credential_present": self.credential_present,
            "version": self.version,
        }


@dataclass(frozen=True)
class RecoverySnapshot:
    snapshot_id: str
    version: int
    purpose: str
    created_at: datetime


@dataclass(frozen=True)
class NetworkStatus:
    ap_reachable: ReachabilitySignal
    external_wifi_connected: ReachabilitySignal
    internet_reachable: ReachabilitySignal
    central_server_reachable: ReachabilitySignal
    ap_state: AccessPointState
    sta_state: StationState
    interfaces: tuple[InterfaceIdentity, ...]
    observed_at: datetime
    stale: bool
    source: str = "PC_MOCK"
    manual_config_url: str | None = None
    last_known_good_version: int | None = None
    retry_count: int = 0
    retry_budget: int = 3

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", ensure_utc(self.observed_at))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "scope03.v1",
            "evidence_class": "TESTED_ON_PC_MOCK",
            "ap_reachable": self.ap_reachable.as_dict(),
            "external_wifi_connected": self.external_wifi_connected.as_dict(),
            "internet_reachable": self.internet_reachable.as_dict(),
            "central_server_reachable": self.central_server_reachable.as_dict(),
            "ap_state": self.ap_state.value,
            "sta_state": self.sta_state.value,
            "interfaces": [
                {"name": item.name, "purpose": item.purpose, "verified": item.verified, "physical_path": item.physical_path}
                for item in self.interfaces
            ],
            "observed_at": self.observed_at.isoformat(),
            "stale": self.stale,
            "source": self.source,
            "manual_config_url": self.manual_config_url,
            "last_known_good_version": self.last_known_good_version,
            "retry_count": self.retry_count,
            "retry_budget": self.retry_budget,
        }
