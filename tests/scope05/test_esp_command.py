from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pi5.telemetry.esp_command import (
    EspCommandError,
    EspFlightAuthorizationBridge,
    auth_allow,
    auth_deny,
    build_command,
    checksum,
    set_max_altitude,
    set_pid,
)
from pi5.telemetry.esp_usb import UsbSerialLineReader


def test_checksum_matches_nmea_xor():
    # Known NMEA example: $GPGLL,5300.97914,N,00259.98174,E,125926,A*28
    assert checksum("GPGLL,5300.97914,N,00259.98174,E,125926,A") == "28"


def test_command_lines_are_checksummed_and_bounded():
    line = auth_allow(600, "REQ-1")
    assert line.startswith(b"$AUTH,ALLOW,600,REQ-1*") and line.endswith(b"\n")
    assert auth_deny("abc/../x") == build_command("AUTH", "DENY", "abc____x")
    assert set_pid("roll", 1.2, 0.3, 0.03) == build_command("PID", "roll", "1.2", "0.3", "0.03")
    assert set_max_altitude(80) == build_command("MAXALT", "80")


@pytest.mark.parametrize(
    "call",
    [
        lambda: auth_allow(0, "x"),
        lambda: auth_allow(86_401, "x"),
        lambda: set_pid("motor", 1, 1, 1),
        lambda: set_pid("roll", float("nan"), 0, 0),
        lambda: set_pid("roll", 1, 1, 99),
        lambda: set_max_altitude(1000),
        lambda: build_command("AUTH,ALLOW"),
    ],
)
def test_invalid_commands_are_rejected(call):
    with pytest.raises(EspCommandError):
        call()


def test_bridge_never_allows_without_live_approval():
    sent: list[bytes] = []
    now = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
    bridge = EspFlightAuthorizationBridge(sent.append, clock=lambda: now)

    assert bridge.refresh().startswith(b"$AUTH,DENY,NONE*")
    bridge.apply_decision("R1", "APPROVED", now + timedelta(minutes=10))
    assert sent[-1].startswith(b"$AUTH,ALLOW,600,R1*")
    bridge.apply_decision("R1", "REJECTED")
    assert sent[-1].startswith(b"$AUTH,DENY,R1*")
    with pytest.raises(EspCommandError):
        bridge.apply_decision("R2", "APPROVED", None)


def test_bridge_expired_approval_becomes_deny():
    sent: list[bytes] = []
    clock = {"now": datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)}
    bridge = EspFlightAuthorizationBridge(sent.append, clock=lambda: clock["now"])
    bridge.apply_decision("R1", "APPROVED", clock["now"] + timedelta(seconds=30))
    clock["now"] += timedelta(seconds=31)
    assert bridge.refresh().startswith(b"$AUTH,DENY,R1*")


def test_reader_is_read_only_unless_commands_enabled():
    reader = UsbSerialLineReader("/dev/ttyUSB0")
    with pytest.raises(PermissionError):
        reader.write_line(b"$PING*16\n")


def test_bridge_exposes_no_arm_or_motor_command():
    names = {n.lower() for n in dir(EspFlightAuthorizationBridge)}
    assert not any("arm" == n or "motor" in n or "disarm" in n for n in names)
