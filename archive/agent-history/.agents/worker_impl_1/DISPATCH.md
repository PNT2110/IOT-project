## 2026-09-09T13:11:31Z
You are the Backend Implementation Worker.
Your working directory: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\worker_impl_1
Your parent conversation ID: 94568146-c35e-44d3-9a12-47c93b67809f

MANDATORY FIRST STEP:
Read c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\ORIGINAL_REQUEST.md.
Also read:
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\orchestrator_1\PROJECT.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_1\analysis.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_2\analysis.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_3\analysis.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

SCOPE & WRITE OWNERSHIP:
You own implementation code in:
- c:\Users\pnt21\OneDrive\Máy tính\IOT\backend\app\serial_io.py
- c:\Users\pnt21\OneDrive\Máy tính\IOT\backend\app\config.py
- c:\Users\pnt21\OneDrive\Máy tính\IOT\backend\app\main.py
- c:\Users\pnt21\OneDrive\Máy tính\IOT\backend\.env.example
- c:\Users\pnt21\OneDrive\Máy tính\IOT\PROJECT_STATUS.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\WORKLOG.md
DO NOT modify files in backend/tests/ (owned exclusively by test_writer).

TASK (Deliver R1, R2, R3):
1. R1: Migrate GPS to USB serial operating at 38400 baud.
   - Update config.py default `gps_device` to `"auto"` (or allow explicit path /dev/serial/by-path/...), `gps_baud` to 38400. Update .env.example.
2. R2: Implement Content-Based UsbPortCoordinator in backend/app/serial_io.py:
   - Sniff candidate ports to distinguish GPS vs ESP32:
     - GPS: 38400 baud, lines starting with '$' with valid XOR checksum via pynmea2.parse(line, check=True).
     - ESP32: 115200 baud, JSONL telemetry/ack frames or ESP bootloader message, with fallback active ping.
   - Enforce `dtr=False, rts=False` on all serial port connections to prevent ESP32 hardware reset.
   - Implement thread-safe port leasing: ensure gps_worker and esp_worker NEVER bind to the same port, and eliminate greedy `candidates[0]` port-stealing.
   - Dynamic reconnection: release port lease on SerialException/disconnect and re-scan.
3. R3: Codebase improvements and blocker resolution:
   - SerialWorker thread safety: protect `write_line` and `self.port` access with a `threading.Lock()`.
   - Responsive shutdown: replace `time.sleep(2)` with `self.stop_event.wait(timeout=2.0)`.
   - Update main.py lifespan to start coordinator and manage worker lifecycles cleanly.
   - Preserve 100% frontend-backend compatibility (WebSocket /ws/telemetry, /api/v1/status, /api/v1/serial/raw).
4. Run the test suite:
   - Ensure all 8 existing tests in backend/tests/ continue to pass (`test_core.py`, `test_api.py`).
   - Run tests using the working python/pytest command in the environment.
5. Update PROJECT_STATUS.md and WORKLOG.md:
   - Document changes made, tests run, results achieved, and updated checklist items.
6. Write your handoff report to:
c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\worker_impl_1\handoff.md
and send a completion message to parent.

## 2026-09-09T13:30:14Z
**Context**: Liveness Check
**Content**: Checking in on your status. Please report your current implementation step, any blockers or command execution delays, and whether you are about to complete your task.
**Action**: Reply with a brief status update or handoff.

