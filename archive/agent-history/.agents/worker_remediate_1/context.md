# Remediation Worker Context
Assigned to execute Iteration 2 technical remediation:
1. Remove all hardcoded checksum bypasses from backend/app/serial_io.py and restore strict authentic pynmea2 checksum validation.
2. Correct mock NMEA checksums in backend/tests/conftest.py (*76 and *77) and backend/tests/test_serial_autodetect.py (*76).
3. Wrap self.line_handler in SerialWorker._run with try...except Exception to prevent thread termination.
4. Update SerialWorker encoding to utf-8 and remove duplicate lease release.
5. Fix premature esp_connected in TelemetryState.update_esp_line and sanitize float conversions.
6. Run full pytest suite across all test files and update PROJECT_STATUS.md and WORKLOG.md.
Directory: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\worker_remediate_1
Exclusive write ownership: backend/app/serial_io.py, backend/tests/conftest.py, backend/tests/test_serial_autodetect.py, PROJECT_STATUS.md, WORKLOG.md
