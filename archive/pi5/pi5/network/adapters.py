from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from .models import InterfaceIdentity, ProfileDraft, ReachabilitySignal, RecoverySnapshot, SignalState, utcnow
from .validation import validate_interface_name, validate_sta_profile


class NetworkManagerAdapter(Protocol):
    def discover_interfaces(self) -> tuple[InterfaceIdentity, ...]: ...

    def propose_profile(self, *, interface: InterfaceIdentity, ssid: str, password: str, version: int) -> ApplyProposal: ...


class ConnectivityProbe(Protocol):
    def probe(self, signal_name: str) -> ReachabilitySignal: ...


class ProfileStore(Protocol):
    def save_draft(self, profile: ProfileDraft, *, expected_version: int | None) -> ProfileDraft: ...

    def commit_last_known_good(self, *, purpose: str, expected_version: int) -> RecoverySnapshot: ...

    def rollback(self, *, purpose: str, expected_version: int) -> RecoverySnapshot: ...


class RecoveryController(Protocol):
    def snapshot(self, *, purpose: str, version: int) -> RecoverySnapshot: ...

    def rollback(self, snapshot: RecoverySnapshot) -> RecoverySnapshot: ...


@dataclass(frozen=True)
class ApplyProposal:
    profile: ProfileDraft
    applied: bool = False
    requires_live_authorization: bool = True
    commands: tuple[str, ...] = ()


class MockNetworkManagerAdapter:
    """Offline adapter: it can discover/propose, never apply or call an OS service."""

    def __init__(self, interfaces: tuple[InterfaceIdentity, ...]) -> None:
        self._interfaces = interfaces

    def discover_interfaces(self) -> tuple[InterfaceIdentity, ...]:
        return self._interfaces

    def propose_profile(self, *, interface: InterfaceIdentity, ssid: str, password: str, version: int) -> ApplyProposal:
        if interface not in self._interfaces or not interface.verified or interface.purpose != "usb_sta":
            raise ValueError("only a verified USB STA interface may receive a mock STA proposal")
        metadata = validate_sta_profile(interface_name=interface.name, ssid=ssid, password=password)
        profile = ProfileDraft(purpose="usb_sta", interface_name=str(metadata["interface_name"]), ssid=str(metadata["ssid"]), credential_present=True, version=version)
        return ApplyProposal(profile=profile)

    def apply(self, _proposal: ApplyProposal) -> None:
        raise PermissionError("live network apply is disabled in the PC mock")


class MockConnectivityProbe:
    def __init__(self, signals: dict[str, ReachabilitySignal] | None = None) -> None:
        self._signals = dict(signals or {})

    def set_signal(self, signal_name: str, signal: ReachabilitySignal) -> None:
        self._signals[signal_name] = signal

    def probe(self, signal_name: str) -> ReachabilitySignal:
        return self._signals.get(signal_name, ReachabilitySignal(state=SignalState.UNKNOWN, observed_at=utcnow(), source="PC_MOCK", stale=True, error_code="UNCONFIGURED"))


class InMemoryProfileStore:
    def __init__(self) -> None:
        self._drafts: dict[str, ProfileDraft] = {}
        self._last_known_good: dict[str, ProfileDraft] = {}

    def save_draft(self, profile: ProfileDraft, *, expected_version: int | None) -> ProfileDraft:
        current = self._drafts.get(profile.purpose) or self._last_known_good.get(profile.purpose)
        current_version = current.version if current else 0
        if expected_version is not None and expected_version != current_version:
            raise ValueError("profile version conflict")
        if profile.version != current_version + 1:
            raise ValueError("profile version must advance exactly once")
        self._drafts[profile.purpose] = profile
        return profile

    def get_draft(self, purpose: str) -> ProfileDraft | None:
        return self._drafts.get(purpose)

    def get_last_known_good(self, purpose: str) -> ProfileDraft | None:
        return self._last_known_good.get(purpose)

    def commit_last_known_good(self, *, purpose: str, expected_version: int) -> RecoverySnapshot:
        draft = self._drafts.get(purpose)
        if not draft or draft.version != expected_version:
            raise ValueError("draft version is not available for commit")
        self._last_known_good[purpose] = draft
        return RecoverySnapshot(snapshot_id=str(uuid4()), version=draft.version, purpose=purpose, created_at=utcnow())

    def rollback(self, *, purpose: str, expected_version: int) -> RecoverySnapshot:
        known_good = self._last_known_good.get(purpose)
        if not known_good or known_good.version != expected_version:
            raise ValueError("last-known-good profile version is not available")
        self._drafts[purpose] = known_good
        return RecoverySnapshot(snapshot_id=str(uuid4()), version=known_good.version, purpose=purpose, created_at=utcnow())


class MockRecoveryController:
    def __init__(self) -> None:
        self.rollback_count = 0

    def snapshot(self, *, purpose: str, version: int) -> RecoverySnapshot:
        return RecoverySnapshot(snapshot_id=str(uuid4()), version=version, purpose=purpose, created_at=utcnow())

    def rollback(self, snapshot: RecoverySnapshot) -> RecoverySnapshot:
        self.rollback_count += 1
        return snapshot
