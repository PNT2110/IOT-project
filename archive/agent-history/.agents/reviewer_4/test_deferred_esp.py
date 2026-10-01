import json
import time
from app.serial_io import TelemetryState

def test_deferred_esp():
    state = TelemetryState()
    assert state.snapshot().esp_connected is False

    # 1. Non-JSON lines do NOT set esp_connected
    for non_json in ["$GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,*76",
                     "OK", "AT+CGMI", "GARBAGE\x00\xff", "", "   ", "12345", "[1, 2, 3]"]:
        state.update_esp_line(non_json)
        assert state.snapshot().esp_connected is False, f"esp_connected became True on non-JSON: {non_json}"

    # 2. Valid JSON dict sets esp_connected
    state.update_esp_line(json.dumps({"type": "telemetry", "attitude": {"roll": 10.0}}))
    assert state.snapshot().esp_connected is True
    assert state.snapshot().attitude.roll == 10.0

    print("Deferred esp_connected passed all tests!")

test_deferred_esp()
