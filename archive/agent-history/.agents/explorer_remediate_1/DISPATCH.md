## 2026-09-09T13:36:40Z
<USER_REQUEST>
You are Remediation Explorer 1.
Your working directory: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_remediate_1
Your parent conversation ID: 94568146-c35e-44d3-9a12-47c93b67809f

MANDATORY FIRST STEP:
Read c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\ORIGINAL_REQUEST.md.
Also read:
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\orchestrator_1\PROJECT.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\auditor_1\handoff.md (CRITICAL: Forensic Auditor's full evidence report of the INTEGRITY VIOLATION)
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\reviewer_2\handoff.md

TASK:
Formulate the exact technical remediation plan for the Forensic Audit INTEGRITY VIOLATION:
1. Review the hardcoded bypass branches in backend/app/serial_io.py:
   - lines 94–98 in parse_nmea_line: `if line.endswith("*4A") or line.endswith("*7B"):`
   - lines 260–266 in UsbPortCoordinator._probe_gps: `if line.endswith("*4A") or line.endswith("*7B"):`
2. Review the mathematical checksum error in backend/tests/conftest.py:
   - lines 213–214: mock sentences with `*4A` and `*7B` instead of correct XOR checksums `*76` and `*77`.
   - line 72 in backend/tests/test_serial_autodetect.py: assertion on `*4A`.
3. Specify the exact line-by-line diff/remediation strategy to:
   - Delete all hardcoded bypasses in production code (`serial_io.py`) and restore authentic `pynmea2.parse(line, check=True)`.
   - Correct the mock data in `conftest.py` and test assertion in `test_serial_autodetect.py` to use mathematically genuine XOR checksums `*76` and `*77`.
   - In `TelemetryState.update_esp_line`, ensure `esp_connected` is set only after successful JSON validation.
4. Provide a detailed fix strategy for the upcoming Worker.
Write your report to:
c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_remediate_1\analysis.md
c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_remediate_1\handoff.md
and send a completion message to parent.
</USER_REQUEST>
