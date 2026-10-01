import json
from app.serial_io import TelemetryState, _safe_float

state = TelemetryState()

adversarial_floats = [
    "NaN", "nan", "-NaN", "Infinity", "-Infinity", "inf", "-inf",
    1e309, -1e309, None, [], {}, "corrupt_string", 0, -0.0, 12.34
]

for val in adversarial_floats:
    payload = {
        "type": "telemetry",
        "attitude": {"roll": val, "pitch": val, "yaw": val},
        "armed": True,
        "flight_mode": "STABILIZE"
    }
    line = json.dumps(payload)
    state.update_esp_line(line)
    snap = state.snapshot()
    # Ensure serialization to JSON works without ValueError
    dumped = snap.model_dump_json()
    assert "NaN" not in dumped and "Infinity" not in dumped, f"Unsafe float leaked into JSON: {dumped}"
    parsed_json = json.loads(dumped)
    assert isinstance(parsed_json["attitude"]["roll"], (int, float))

print("All adversarial float payloads safely handled and serialized without NaN/Inf leaks!")
