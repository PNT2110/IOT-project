from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from pi5.telemetry.esp_usb import (
    ESP_USB_SCHEMA,
    EspUsbFrameError,
    ReadOnlyEspUsbTelemetrySource,
    UsbSerialLineReader,
    parse_esp_frame,
)


CAPTURE = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)


def frame(sequence: int = 1) -> str:
    return json.dumps({
        "schema_version": ESP_USB_SCHEMA,
        "seq": sequence,
        "imu": {"roll_deg": 0.4, "pitch_deg": -1.2, "yaw_deg": 18.0},
        "baro": {"altitude_m": 12.3, "vertical_speed_mps": 0.1},
        "power": {"battery_pct": 83.0, "voltage_v": 15.7},
        "temperature_c": 31.2,
        "sbus": {"signal_ok": True, "channels": [1500, 1500, 1000, 1500]},
        "gnss": {"fix_state": "VALID_FIX", "latitude": 10.0, "longitude": 106.0, "altitude_m": 12.1},
        "flight": {"arm_state": "DISARMED", "mode": "ANGLE"},
        "pid": {"roll": {"kp": 1.2, "ki": 0.1, "kd": 0.02}},
    })


def test_parse_esp_frame_preserves_sensor_groups():
    parsed = parse_esp_frame(frame(), capture_timestamp=CAPTURE)

    assert parsed.sequence == 1
    assert parsed.roll_deg == 0.4
    assert parsed.battery_pct == 83.0
    assert parsed.latitude == 10.0
    assert parsed.sbus_channels == (1500, 1500, 1000, 1500)
    assert parsed.flight_status["arm_state"] == "DISARMED"
    assert parsed.pid["roll"]["kp"] == 1.2


def test_usb_web_source_maps_valid_frame_and_rejects_replay():
    lines = iter([frame(1), frame(1)])
    source = ReadOnlyEspUsbTelemetrySource(lambda timeout: next(lines, ""))

    first = source.read()
    replay = source.read()

    assert first["source"] == "ESP32_USB_SERIAL"
    assert first["fix_state"] == "FIX"
    assert first["device"]["power"]["battery_pct"] == 83.0
    assert replay["fix_state"] == "UNAVAILABLE"
    assert replay["device"]["error"] == "ESP_USB_SEQUENCE_REPLAY"


def test_usb_web_source_counts_skipped_frames_instead_of_failing():
    # Pi chi doc frame moi nhat, nen bo qua frame cu la hop le nhung phai duoc dem.
    lines = iter([frame(1), frame(3)])
    source = ReadOnlyEspUsbTelemetrySource(lambda timeout: next(lines, ""))

    assert source.read()["fix_state"] == "FIX"
    gap = source.read()

    assert gap["fix_state"] == "FIX"
    assert gap["device"]["dropped_frames"] == 1


def test_usb_source_without_device_never_invents_values():
    sample = ReadOnlyEspUsbTelemetrySource().read()

    assert sample["fix_state"] == "UNAVAILABLE"
    assert sample["latitude"] is None
    assert sample["device"]["error"] == "ESP_USB_NOT_CONFIGURED"


def test_pi_asgi_entrypoint_uses_esp_usb_boundary_without_opening_a_device():
    import pi5.web.asgi as asgi

    assert asgi.app.state.telemetry.read()["device"]["error"] == "ESP_USB_NOT_CONFIGURED"


def test_cp2102_by_id_path_is_allowed_but_arbitrary_serial_path_is_not():
    reader = UsbSerialLineReader("/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART")
    assert reader.device_path.endswith("CP2102_USB_to_UART")
    with pytest.raises(ValueError):
        UsbSerialLineReader("/dev/serial/by-id/usb-other-device")


@pytest.mark.parametrize("payload", [
    {"schema_version": ESP_USB_SCHEMA, "seq": 1, "gnss": {"latitude": 91, "longitude": 106}},
    {"schema_version": ESP_USB_SCHEMA, "seq": 1, "sbus": {"channels": [3000]}},
    {"schema_version": "other", "seq": 1},
])
def test_parse_esp_frame_rejects_invalid_or_unsafe_values(payload: dict[str, object]):
    with pytest.raises(EspUsbFrameError):
        parse_esp_frame(json.dumps(payload), capture_timestamp=CAPTURE)



def test_parse_esp_frame_accepts_blocked_mode_and_pi_link_reason():
    import json as _json
    data = _json.loads(frame(7))
    data["flight"] = {"arm_state": "BLOCKED", "mode": "BLOCKED", "arm_block_reason": "PI_LINK_LOST", "authorization": "ALLOWED"}
    data["link"] = {"pi_alive": False, "pi_heartbeat_age_ms": 12000}
    parsed = parse_esp_frame(_json.dumps(data), capture_timestamp=CAPTURE)
    device = parsed.device_data()
    assert device["flight"]["arm_state"] == "BLOCKED"
    assert device["flight"]["mode"] == "BLOCKED"
    assert device["flight"]["arm_block_reason"] == "PI_LINK_LOST"
    assert device["link"]["pi_alive"] is False
