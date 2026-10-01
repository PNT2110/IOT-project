import sys
import threading
import time
import json
import uuid

sys.path.insert(0, r"c:\Users\pnt21\OneDrive\Máy tính\IOT\backend")

from app.serial_io import parse_nmea_line, is_valid_nmea_checksum, TelemetryState, UsbPortCoordinator

def test_stress():
    print("[Stress Test] Running adversarial edge cases and thread concurrency...")
    
    # 1. Edge case NMEA inputs:
    edge_cases = [
        "", "\n", " ", "\t", "$", "$*", "$*00", "$GGA*",
        "$GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,*76\r\n", # with CRLF
        " $GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,*76", # leading space (should return None per startswith('$'))
        "$GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,*76EXTRA", # extra characters
        "$GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,*7", # truncated checksum
        "$GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,", # missing checksum
    ]
    for case in edge_cases:
        # None of these should throw unhandled exceptions
        try:
            res = parse_nmea_line(case)
        except Exception as e:
            assert False, f"Unhandled exception on case {case!r}: {e}"

    # 2. Concurrency stress test on TelemetryState:
    st = TelemetryState()
    errors = []

    def writer_gps():
        for i in range(100):
            try:
                line = "$GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,*76"
                p = parse_nmea_line(line)
                if p:
                    st.update_gps(p)
            except Exception as e:
                errors.append(e)

    def writer_esp():
        for i in range(100):
            try:
                cid = str(uuid.uuid4())
                st.update_esp_line(json.dumps({"type": "ack", "command_id": cid, "accepted": True}))
                st.update_esp_line(json.dumps({"type": "telemetry", "attitude": {"roll": float(i)}}))
                st.take_ack(cid)
            except Exception as e:
                errors.append(e)

    def reader():
        for i in range(100):
            try:
                snap = st.snapshot()
                d = snap.model_dump()
            except Exception as e:
                errors.append(e)

    threads = [
        threading.Thread(target=writer_gps),
        threading.Thread(target=writer_esp),
        threading.Thread(target=reader),
        threading.Thread(target=writer_gps),
        threading.Thread(target=reader),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Encountered concurrency errors: {errors}"
    print("[Stress Test] Concurrency & edge cases: 100% PASS with 0 errors!")

if __name__ == "__main__":
    test_stress()
