from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .models import AccessPointState, InterfaceIdentity, NetworkStatus, ReachabilitySignal, SignalState, StationState, utcnow


class NetworkEvent(str, Enum):
    AP_READY = "AP_READY"
    AP_LOST = "AP_LOST"
    STA_CONNECTING = "STA_CONNECTING"
    STA_CONNECTED = "STA_CONNECTED"
    STA_FAILED = "STA_FAILED"
    STA_DISCONNECTED = "STA_DISCONNECTED"
    RETRY = "RETRY"
    CANCEL = "CANCEL"
    INTERNET_UP = "INTERNET_UP"
    INTERNET_DOWN = "INTERNET_DOWN"
    PC_UP = "PC_UP"
    PC_DOWN = "PC_DOWN"
    RESTART = "RESTART"


@dataclass(frozen=True)
class TransitionResult:
    event: NetworkEvent
    accepted: bool
    reason: str
    status: NetworkStatus


class PiNetworkStateMachine:
    """Deterministic state model; no I/O, system-process, root helper or auto-apply."""

    def __init__(self, *, interfaces: tuple[InterfaceIdentity, ...], retry_budget: int = 3, manual_config_url: str | None = None) -> None:
        if retry_budget < 0:
            raise ValueError("retry_budget must not be negative")
        self.interfaces = interfaces
        self.retry_budget = retry_budget
        self.manual_config_url = manual_config_url
        self.ap_state = AccessPointState.UP
        self.sta_state = StationState.DISCONNECTED
        self.retry_count = 0
        now = utcnow()
        self._ap = ReachabilitySignal(SignalState.UP, now, "PC_MOCK")
        self._external = ReachabilitySignal(SignalState.UNKNOWN, now, "PC_MOCK", stale=True, error_code="NOT_PROBED")
        self._internet = ReachabilitySignal(SignalState.UNKNOWN, now, "PC_MOCK", stale=True, error_code="NOT_PROBED")
        self._central = ReachabilitySignal(SignalState.UNKNOWN, now, "PC_MOCK", stale=True, error_code="NOT_PROBED")

    def status(self, *, observed_at: datetime | None = None, stale: bool = False, last_known_good_version: int | None = None) -> NetworkStatus:
        return NetworkStatus(self._ap, self._external, self._internet, self._central, self.ap_state, self.sta_state, self.interfaces, observed_at or utcnow(), stale, manual_config_url=self.manual_config_url, last_known_good_version=last_known_good_version, retry_count=self.retry_count, retry_budget=self.retry_budget)

    def set_probe(self, signal_name: str, signal: ReachabilitySignal) -> NetworkStatus:
        if signal_name == "external_wifi_connected":
            self._external = signal
        elif signal_name == "internet_reachable":
            self._internet = signal
        elif signal_name == "central_server_reachable":
            self._central = signal
        elif signal_name == "ap_reachable":
            self._ap = signal
            self.ap_state = AccessPointState.UP if signal.state == SignalState.UP else AccessPointState.DEGRADED
        else:
            raise ValueError("unknown probe signal")
        return self.status(observed_at=signal.observed_at)

    def transition(self, event: NetworkEvent) -> TransitionResult:
        accepted = True
        reason = "accepted"
        if event == NetworkEvent.AP_READY:
            self.ap_state = AccessPointState.UP
            self._ap = ReachabilitySignal(SignalState.UP, utcnow(), "PC_MOCK")
        elif event == NetworkEvent.AP_LOST:
            self.ap_state = AccessPointState.DEGRADED
            self._ap = ReachabilitySignal(SignalState.DOWN, utcnow(), "PC_MOCK", error_code="AP_UNAVAILABLE")
        elif event == NetworkEvent.STA_CONNECTING:
            self.sta_state = StationState.CONNECTING
        elif event == NetworkEvent.STA_CONNECTED:
            self.sta_state = StationState.CONNECTED
            self.retry_count = 0
            self._external = ReachabilitySignal(SignalState.UP, utcnow(), "PC_MOCK")
        elif event == NetworkEvent.STA_FAILED:
            self.sta_state = StationState.FAILED
            self.retry_count += 1
            self._external = ReachabilitySignal(SignalState.DOWN, utcnow(), "PC_MOCK", error_code="STA_FAILED")
        elif event == NetworkEvent.STA_DISCONNECTED:
            self.sta_state = StationState.DISCONNECTED
            self._external = ReachabilitySignal(SignalState.DOWN, utcnow(), "PC_MOCK", error_code="STA_DISCONNECTED")
        elif event == NetworkEvent.RETRY:
            if self.retry_count >= self.retry_budget:
                accepted = False
                reason = "retry budget exhausted"
            else:
                self.sta_state = StationState.CONNECTING
        elif event == NetworkEvent.CANCEL:
            if self.sta_state == StationState.CONNECTING:
                self.sta_state = StationState.DISCONNECTED
            else:
                accepted = False
                reason = "no connecting operation to cancel"
        elif event == NetworkEvent.INTERNET_UP:
            self._internet = ReachabilitySignal(SignalState.UP, utcnow(), "PC_MOCK")
        elif event == NetworkEvent.INTERNET_DOWN:
            self._internet = ReachabilitySignal(SignalState.DOWN, utcnow(), "PC_MOCK", error_code="INTERNET_UNREACHABLE")
        elif event == NetworkEvent.PC_UP:
            self._central = ReachabilitySignal(SignalState.UP, utcnow(), "PC_MOCK")
        elif event == NetworkEvent.PC_DOWN:
            self._central = ReachabilitySignal(SignalState.DOWN, utcnow(), "PC_MOCK", error_code="CENTRAL_UNREACHABLE")
        elif event == NetworkEvent.RESTART:
            self.ap_state = AccessPointState.UP
            self.sta_state = StationState.DISCONNECTED
            self.retry_count = 0
            now = utcnow()
            self._ap = ReachabilitySignal(SignalState.UP, now, "PC_MOCK")
            self._external = ReachabilitySignal(SignalState.UNKNOWN, now, "PC_MOCK", stale=True, error_code="NOT_PROBED")
            self._internet = ReachabilitySignal(SignalState.UNKNOWN, now, "PC_MOCK", stale=True, error_code="NOT_PROBED")
            self._central = ReachabilitySignal(SignalState.UNKNOWN, now, "PC_MOCK", stale=True, error_code="NOT_PROBED")
        else:
            accepted = False
            reason = "unknown event"
        return TransitionResult(event, accepted, reason, self.status())
