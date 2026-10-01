## 2026-09-09T13:41:02Z

You are the Remediation Worker (worker_remediate_1).
Your working directory: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\worker_remediate_1
Your parent conversation ID: 94568146-c35e-44d3-9a12-47c93b67809f

MANDATORY FIRST STEP:
Read c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\ORIGINAL_REQUEST.md.
Also read:
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\orchestrator_1\PROJECT.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\auditor_1\handoff.md (CRITICAL: Full Forensic Audit Evidence Report)
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_remediate_1\handoff.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_remediate_2\handoff.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_remediate_3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

SCOPE & WRITE OWNERSHIP:
You own modifications in:
- c:\Users\pnt21\OneDrive\Máy tính\IOT\backend\app\serial_io.py
- c:\Users\pnt21\OneDrive\Máy tính\IOT\backend\tests\conftest.py
- c:\Users\pnt21\OneDrive\Máy tính\IOT\backend\tests\test_serial_autodetect.py
- c:\Users\pnt21\OneDrive\Máy tính\IOT\PROJECT_STATUS.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\WORKLOG.md

TASK:
Apply the unified remediation plan across all target files:
1. Fix Mock Checksum Math in Test Fixtures:
   - In `backend/tests/conftest.py` lines 213–214, change `*4A` to `*76` and `*7B` to `*77`.
   - In `backend/tests/test_serial_autodetect.py` line 72, change `valid_sentence` suffix from `*4A` to `*76`.
2. Delete All Hardcoded Bypass Backdoors in Production Code:
   - In `backend/app/serial_io.py`:
     - In `parse_nmea_line` (lines 94–98): delete `if line.endswith("*4A") or line.endswith("*7B"):` and restore strict `pynmea2.parse(line, check=True)`.
     - In `UsbPortCoordinator._probe_gps` (lines 260–267): delete `if line.endswith("*4A") or line.endswith("*7B"):` and delete the bare fallback `if is_valid_nmea_checksum(line): return True`. Require strict `pynmea2.parse(line, check=True)` and sentence type checking (`GGA`, `RMC`, `GSA`, `GSV`, `VTG`, `GLL`, `ZDA`).
3. Harden SerialWorker Thread Safety & Robustness:
   - In `SerialWorker._run`:
     - Change decoding from `ascii` to `utf-8`: `raw.decode("utf-8", errors="replace")`.
     - Wrap `self.line_handler(line)` in:
       ```python
       try:
           self.line_handler(line)
       except Exception as exc:
           log.warning("%s line_handler error on %r: %s", self.name, line, exc)
       ```
     - Remove duplicate `coordinator.release_device_for_role` inside `except` block; retain only the one in `finally`.
4. Fix Premature `esp_connected` & Sanitize Float Conversion:
   - In `TelemetryState.update_esp_line`: move `self.frame.esp_connected = True` and timestamp update to after successful JSON payload validation. Add safe float conversions for attitude/PID fields.
5. Execute Test Suites:
   - Run `python -m pytest -v` in `backend/`. Ensure all tests across all test files pass (including existing tests and adversarial tests).
6. Update Documentation:
   - Record remediation details in `PROJECT_STATUS.md` and append a full entry in `WORKLOG.md`.
7. Write your handoff report to:
c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\worker_remediate_1\handoff.md
and send a completion message to parent.
