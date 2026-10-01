## 2026-09-09T13:11:31Z
You are the E2E Test Architect (Test Writer).
Your working directory: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\test_writer_e2e_1
Your parent conversation ID: 94568146-c35e-44d3-9a12-47c93b67809f

MANDATORY FIRST STEP:
Read c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\ORIGINAL_REQUEST.md.
Also read:
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\orchestrator_1\PROJECT.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_2\analysis.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_3\analysis.md

SCOPE & WRITE OWNERSHIP:
You own writing the E2E test suite in:
- c:\Users\pnt21\OneDrive\Máy tính\IOT\backend\tests\test_serial_autodetect.py
- c:\Users\pnt21\OneDrive\Máy tính\IOT\backend\tests\conftest.py (if needed)
- c:\Users\pnt21\OneDrive\Máy tính\IOT\TEST_INFRA.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\TEST_READY.md
DO NOT modify any implementation code in backend/app/.

TASK:
Design and implement a comprehensive opaque-box test suite using pytest to verify USB serial auto-detection and concurrent device handling:
1. Build a robust, cross-platform in-memory MockSerialPort fixture and mock `serial.tools.list_ports.comports()` that works deterministically on Windows and Linux without POSIX pty limitations.
2. Implement systematic test tiers per Project Pattern:
   - Tier 1 (Feature Coverage, >=5 tests): Verify GPS NMEA auto-detection at 38400 baud, ESP32 JSONL auto-detection at 115200 baud, XOR checksum validation, JSON format validation, and baud rate configuration.
   - Tier 2 (Boundary & Corner Cases, >=5 tests): Swapped port enumeration (e.g. /dev/ttyUSB0 has ESP32 and /dev/ttyUSB1 has GPS), identical CH340 VID:PID simulation, noise/garbage bytes before valid sentence, empty/silent streams, DTR/RTS flags set to False to protect ESP32 hardware reset, dynamic unplug/port loss.
   - Tier 3 (Cross-Feature Combinations): Concurrent dual-port binding without cross-talk or race conditions, preventing greedy port-stealing, port release and re-lease upon device reconnect.
   - Tier 4 (Real-World Workloads): End-to-end telemetry streaming simulation through coordinator into workers, command dispatching under concurrent telemetry, verification that existing test suite semantics remain intact.
3. Verify test execution using pytest. Ensure all tests run cleanly and fast.
4. Publish TEST_INFRA.md and TEST_READY.md summarizing test runner command, tier coverage, and feature checklist.
5. Write your handoff report to:
c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\test_writer_e2e_1\handoff.md
and send a completion message to parent.
