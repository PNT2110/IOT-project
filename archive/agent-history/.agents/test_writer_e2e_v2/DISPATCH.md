## 2026-09-13T09:38:32Z
You are the E2E Test Writer for IOT Drone Station v2 (Track A).
Your working directory: /home/pnt/IOT/.agents/test_writer_e2e_v2
User request record: /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (read section ## 2026-09-13T09:30:16Z)
Specification file: /home/pnt/IOT/prompt-du-an-drone-v2.md (pay special attention to Section 12 and Table 12.1)
Project documentation: /home/pnt/IOT/PROJECT.md and /home/pnt/IOT/TEST_INFRA.md
Survey findings: /home/pnt/IOT/.agents/explorer_v2_survey_3/report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Boundaries:
You have exclusive write ownership of `/home/pnt/IOT/tests/`. DO NOT modify files in `backend/` or `frontend/` or `FC_can_bang/`.

Your Mission:
1. Build a robust, end-to-end automated test runner in `tests/ssh_test_runner.py` that executes all 16 test scenarios specified in Table 12.1 of `prompt-du-an-drone-v2.md`:
   - Scenario 1: ESP32 AP + captive portal
   - Scenario 2: Pi5 online after provisioning
   - Scenario 3: Serial JSONL communication Pi5 ⇄ ESP32
   - Scenario 4: Registration + Email OTP + 2FA TOTP (User active / Admin pending)
   - Scenario 5: Default admin forced email update + OTP before any other action
   - Scenario 6: Mandatory firmware flash before using flight control features
   - Scenario 7: Camera streaming
   - Scenario 8: Telemetry 3D (Roll/Pitch/Yaw + LiDAR altitude)
   - Scenario 9: PID tuning read/write
   - Scenario 10: Flight permission request to MOD server (GPS, time window, license)
   - Scenario 11: Flight permit approval opens 1km radius zone
   - Scenario 12: Flight window expiration automatically closes zone and locks ARM
   - Scenario 13: ARM lock when unauthorized, outside 1km, or outside time window
   - Scenario 14: Firmware management (upload, delete, integrity check)
   - Scenario 15: MOD server registration requires admin approval
   - Scenario 16: Draw & delete no-fly zones (geofence engine update)
2. Support Dual Modes:
   - Remote Mode: connects via Paramiko SSH to Pi5 (`192.168.1.118`, user `pi5`, password `123456` or key) to query endpoints, inspect services, and run commands.
   - Mock/Bench Mode: fallback mode using virtual serial PTY or mocked hardware endpoints for headless local CI verification without crashing when physical hardware is not connected.
3. Structure tests cleanly into modular files (e.g. `tests/test_scenario_01_wifi.py`, `tests/test_scenario_04_auth.py`, etc., or unified runner).
4. Provide structured reporting: outputs `tests/ssh_test_report.json` and human-readable `TEST_REPORT.md` with clear PASS/FAIL logs per scenario, timing, and error tracebacks.
5. Create `/home/pnt/IOT/TEST_READY.md` summarizing the test suite, coverage across the 16 scenarios, and exact runner command.
6. Verify your test runner by running it (in bench/mock mode or remote test) and document results.

Deliverables:
- Test files in `/home/pnt/IOT/tests/`
- `/home/pnt/IOT/TEST_READY.md`
- Work log and handoff in `/home/pnt/IOT/.agents/test_writer_e2e_v2/handoff.md` and `/home/pnt/IOT/.agents/test_writer_e2e_v2/report.md`
When done, notify parent via send_message.
