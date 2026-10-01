from __future__ import annotations

import re


INTERFACE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,31}$")


def validate_interface_name(value: str) -> str:
    if not isinstance(value, str) or not INTERFACE_PATTERN.fullmatch(value):
        raise ValueError("interface name is invalid")
    return value


def validate_ssid(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("SSID must not be empty")
    encoded = value.encode("utf-8")
    if len(encoded) > 32 or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("SSID must be 1-32 UTF-8 bytes without control characters")
    return value


def validate_password(value: str) -> None:
    if not isinstance(value, str) or not 8 <= len(value) <= 63:
        raise ValueError("network credential must be 8-63 characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("network credential contains a control character")


def validate_sta_profile(*, interface_name: str, ssid: str, password: str) -> dict[str, object]:
    """Validate input but intentionally return only redacted metadata."""
    return {
        "interface_name": validate_interface_name(interface_name),
        "ssid": validate_ssid(ssid),
        "credential_present": bool(validate_password(password) is None),
    }
