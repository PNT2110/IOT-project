from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pi5.network.adapters import InMemoryProfileStore, MockConnectivityProbe, MockNetworkManagerAdapter, MockRecoveryController
from pi5.network.contract import status_contract
from pi5.network.models import InterfaceIdentity, ReachabilitySignal, SignalState
from pi5.network.state import NetworkEvent, PiNetworkStateMachine
from pi5.network.validation import validate_password, validate_ssid


INTERFACES = (
    InterfaceIdentity("ap0", "onboard_ap", verified=True, physical_path="mock:onboard"),
    InterfaceIdentity("sta0", "usb_sta", verified=True, physical_path="mock:usb"),
)


def test_profile_proposal_is_typed_redacted_and_never_applied():
    adapter = MockNetworkManagerAdapter(INTERFACES)
    proposal = adapter.propose_profile(interface=INTERFACES[1], ssid="Lab-SSID-✓", password="pass$(not-a-shell-command)", version=1)
    assert proposal.profile.as_redacted() == {"purpose": "usb_sta", "interface_name": "sta0", "ssid": "Lab-SSID-✓", "credential_present": True, "version": 1}
    assert proposal.commands == ()
    assert proposal.applied is False
    assert proposal.requires_live_authorization is True
    with pytest.raises(PermissionError):
        adapter.apply(proposal)
    with pytest.raises(ValueError):
        adapter.propose_profile(interface=InterfaceIdentity("unknown0", "usb_sta"), ssid="Lab", password="password123", version=1)
    assert "pass$(not-a-shell-command)" not in str(proposal.profile.as_redacted())


def test_profile_validation_handles_unicode_controls_and_lengths():
    assert validate_ssid("WiFi-✓") == "WiFi-✓"
    with pytest.raises(ValueError):
        validate_ssid("")
    with pytest.raises(ValueError):
        validate_ssid("x" * 33)
    with pytest.raises(ValueError):
        validate_ssid("bad\nssid")
    with pytest.raises(ValueError):
        validate_password("short")
    with pytest.raises(ValueError):
        validate_password("bad\npassword")


def test_three_signals_are_independent_and_unknown_is_not_success():
    machine = PiNetworkStateMachine(interfaces=INTERFACES, manual_config_url="http://manual.invalid/network")
    initial = status_contract(machine.status())
    assert initial["evidence_class"] == "TESTED_ON_PC_MOCK"
    assert initial["external_wifi_connected"]["state"] == "UNKNOWN"
    assert initial["internet_reachable"]["state"] == "UNKNOWN"
    assert initial["central_server_reachable"]["state"] == "UNKNOWN"
    machine.transition(NetworkEvent.STA_CONNECTED)
    machine.transition(NetworkEvent.INTERNET_DOWN)
    machine.transition(NetworkEvent.PC_UP)
    status = status_contract(machine.status())
    assert status["external_wifi_connected"]["state"] == "UP"
    assert status["internet_reachable"]["state"] == "DOWN"
    assert status["central_server_reachable"]["state"] == "UP"
    assert status["ap_reachable"]["state"] == "UP"
    assert status["manual_config_url"] == "http://manual.invalid/network"


def test_sta_failures_keep_ap_and_retry_budget_is_bounded():
    machine = PiNetworkStateMachine(interfaces=INTERFACES, retry_budget=2)
    machine.transition(NetworkEvent.STA_CONNECTING)
    machine.transition(NetworkEvent.STA_FAILED)
    assert machine.status().ap_state.value == "AP_UP"
    assert machine.status().sta_state.value == "STA_FAILED"
    assert machine.transition(NetworkEvent.RETRY).accepted is True
    machine.transition(NetworkEvent.STA_FAILED)
    assert machine.transition(NetworkEvent.RETRY).accepted is False
    assert machine.transition(NetworkEvent.STA_FAILED).status.ap_state.value == "AP_UP"
    machine.transition(NetworkEvent.AP_LOST)
    assert machine.status().ap_state.value == "AP_DEGRADED"


def test_profile_store_version_concurrency_and_repeated_rollback():
    store = InMemoryProfileStore()
    adapter = MockNetworkManagerAdapter(INTERFACES)
    first = adapter.propose_profile(interface=INTERFACES[1], ssid="Lab", password="password123", version=1).profile
    store.save_draft(first, expected_version=None)
    store.commit_last_known_good(purpose="usb_sta", expected_version=1)
    second = adapter.propose_profile(interface=INTERFACES[1], ssid="Lab-2", password="password456", version=2).profile
    store.save_draft(second, expected_version=1)
    with pytest.raises(ValueError):
        store.save_draft(second, expected_version=1)
    restored = store.rollback(purpose="usb_sta", expected_version=1)
    repeated = store.rollback(purpose="usb_sta", expected_version=1)
    assert restored.version == repeated.version == 1
    assert store.get_draft("usb_sta").ssid == "Lab"
    recovery = MockRecoveryController()
    snapshot = recovery.snapshot(purpose="usb_sta", version=1)
    assert recovery.rollback(snapshot).snapshot_id == snapshot.snapshot_id
    assert recovery.rollback_count == 1


def test_probe_injection_does_not_infer_other_signals():
    observed = datetime(2026, 9, 22, tzinfo=timezone.utc)
    probe = MockConnectivityProbe()
    unknown = probe.probe("internet_reachable")
    assert unknown.state == SignalState.UNKNOWN
    probe.set_signal("external_wifi_connected", ReachabilitySignal(SignalState.UP, observed, "PC_MOCK", latency_ms=4, timeout_ms=500))
    assert probe.probe("external_wifi_connected").state == SignalState.UP
    assert probe.probe("internet_reachable").state == SignalState.UNKNOWN


def test_restart_restores_local_recovery_semantics_without_applying_network():
    machine = PiNetworkStateMachine(interfaces=INTERFACES)
    machine.transition(NetworkEvent.AP_LOST)
    machine.transition(NetworkEvent.STA_FAILED)
    result = machine.transition(NetworkEvent.RESTART)
    assert result.accepted is True
    assert result.status.ap_state.value == "AP_UP"
    assert result.status.sta_state.value == "STA_DISCONNECTED"
    assert result.status.external_wifi_connected.state == SignalState.UNKNOWN
    assert result.status.stale is False
