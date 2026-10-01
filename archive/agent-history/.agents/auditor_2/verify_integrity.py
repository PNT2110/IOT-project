import sys
import os
import json
import uuid

sys.path.insert(0, r"c:\Users\pnt21\OneDrive\Máy tính\IOT\backend")

from app.serial_io import parse_nmea_line, is_valid_nmea_checksum, TelemetryState, UsbPortCoordinator

def test_nmea():
    print("[1] Testing NMEA XOR calculation and validation...")
    s1_valid = "$GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,*76"
    s1_invalid_4a = "$GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,*4A"
    s2_valid = "$GNRMC,123519.00,A,1046.1234,N,10640.5678,E,0.22,120.5,090926,,,A*77"
    s2_invalid_7b = "$GNRMC,123519.00,A,1046.1234,N,10640.5678,E,0.22,120.5,090926,,,A*7B"

    assert is_valid_nmea_checksum(s1_valid) is True, "s1_valid should have valid checksum"
    assert is_valid_nmea_checksum(s1_invalid_4a) is False, "s1_invalid_4a should have invalid checksum"
    assert is_valid_nmea_checksum(s2_valid) is True, "s2_valid should have valid checksum"
    assert is_valid_nmea_checksum(s2_invalid_7b) is False, "s2_invalid_7b should have invalid checksum"

    p1_valid = parse_nmea_line(s1_valid)
    assert p1_valid is not None, "p1_valid should parse successfully"
    assert p1_valid.valid is True
    assert round(p1_valid.latitude, 4) == 10.7687

    p1_bad = parse_nmea_line(s1_invalid_4a)
    assert p1_bad is None, f"Expected None for s1_invalid_4a but got {p1_bad}"

    p2_valid = parse_nmea_line(s2_valid)
    assert p2_valid is not None, "p2_valid should parse successfully"
    assert p2_valid.valid is True

    p2_bad = parse_nmea_line(s2_invalid_7b)
    assert p2_bad is None, f"Expected None for s2_invalid_7b but got {p2_bad}"
    print("  -> NMEA validation: PASS")

def test_esp32():
    print("[2] Testing ESP32 JSON validation and ACK frame processing...")
    st = TelemetryState()

    # Non-JSON or corrupted lines:
    st.update_esp_line("GARBAGE_NOISE")
    assert st.frame.esp_connected is False, "Garbage line should not set esp_connected"
    assert st.last_esp_monotonic == 0.0, "Garbage line should not update last_esp_monotonic"

    st.update_esp_line("rst:0x1 (POWERON_RESET),boot:0x13")
    assert st.frame.esp_connected is False, "Boot string should not set esp_connected"
    assert st.last_esp_monotonic == 0.0

    st.update_esp_line('{"type": "broken_json')
    assert st.frame.esp_connected is False

    # Valid ACK frame:
    cid = str(uuid.uuid4())
    ack_line = json.dumps({"type": "ack", "command_id": cid, "accepted": True, "message": "Command received"})
    st.update_esp_line(ack_line)
    assert st.frame.esp_connected is True, "Valid ACK should set esp_connected"
    assert st.last_esp_monotonic > 0.0
    ack_obj = st.take_ack(cid)
    assert ack_obj is not None, "ACK should be recorded"
    assert str(ack_obj.command_id) == cid
    assert ack_obj.accepted is True
    assert st.take_ack(cid) is None, "ACK should be removed on take"

    # Valid Telemetry frame:
    telem_line = json.dumps({
        "type": "telemetry",
        "armed": True,
        "flight_mode": "AUTO",
        "attitude": {"roll": 5.5, "pitch": -2.1, "yaw": 180.0},
        "pid": {"roll": {"kp": 1.0, "ki": 0.1, "kd": 0.01, "setpoint": 0.0, "measured": 5.5, "output": -5.5}}
    })
    st.update_esp_line(telem_line)
    assert st.frame.armed is True
    assert st.frame.flight_mode == "AUTO"
    assert st.frame.attitude.roll == 5.5
    assert st.frame.pid["roll"].kp == 1.0

    # Telemetry with corrupted float values (NaN, Inf):
    telem_corrupt_float = json.dumps({
        "type": "telemetry",
        "attitude": {"roll": "NaN", "pitch": "Infinity", "yaw": None}
    })
    st.update_esp_line(telem_corrupt_float)
    assert st.frame.attitude.roll == 0.0
    assert st.frame.attitude.pitch == 0.0
    assert st.frame.attitude.yaw == 0.0
    print("  -> ESP32 validation: PASS")

def test_source_code_cleanliness():
    print("[3] Testing source code cleanliness in backend/app/serial_io.py...")
    path = r"c:\Users\pnt21\OneDrive\Máy tính\IOT\backend\app\serial_io.py"
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()

    forbidden = ["*4A", "*7B", "check=False", "check = False"]
    for term in forbidden:
        count = code.count(term)
        assert count == 0, f"Found {count} occurrences of {term} in {path}!"
    print("  -> Source code cleanliness: PASS")

def test_test_suite_nmea_checksums():
    print("[4] Testing mathematical NMEA checksums in conftest.py & test_serial_autodetect.py...")
    import re
    files = [
        r"c:\Users\pnt21\OneDrive\Máy tính\IOT\backend\tests\conftest.py",
        r"c:\Users\pnt21\OneDrive\Máy tính\IOT\backend\tests\test_serial_autodetect.py"
    ]
    pattern = re.compile(r'(\$[A-Za-z0-9,._-]+\*[0-9A-Fa-f]{2})')
    found_sentences = []
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, 1):
                for match in pattern.findall(line):
                    body, claimed_hex = match[1:].split("*")
                    calc_xor = 0
                    for ch in body:
                        calc_xor ^= ord(ch)
                    calc_hex = f"{calc_xor:02X}"
                    is_match = (calc_hex == claimed_hex.upper())
                    found_sentences.append((fpath, idx, match, calc_hex, claimed_hex.upper(), is_match))
                    print(f"  {os.path.basename(fpath)}:{idx} {match} -> Calc: 0x{calc_hex}, Claimed: 0x{claimed_hex.upper()} (Valid: {is_match})")

    # Specifically check the mock sentences
    # conftest.py line 213: *76 (Valid)
    # conftest.py line 214: *77 (Valid)
    # conftest.py line 211: *00 (Intentionally bad checksum)
    # test_serial_autodetect.py line 72: *76 (Valid)
    # test_serial_autodetect.py line 73: *99 (Intentionally bad checksum)
    for fpath, idx, match, calc_hex, claimed_hex, is_match in found_sentences:
        if match.endswith("*76"):
            assert is_match is True, f"{match} should have valid checksum 0x76"
        elif match.endswith("*77"):
            assert is_match is True, f"{match} should have valid checksum 0x77"
        elif match.endswith("*00") or match.endswith("*99"):
            assert is_match is False, f"{match} is intentionally bad and should not match"
    print("  -> Test suite NMEA sentences: ALL MATHEMATICALLY VERIFIED")

if __name__ == "__main__":
    test_nmea()
    test_esp32()
    test_source_code_cleanliness()
    test_test_suite_nmea_checksums()
    print("\nALL AUDIT CHECKS PASSED EMPIRICALLY!")
