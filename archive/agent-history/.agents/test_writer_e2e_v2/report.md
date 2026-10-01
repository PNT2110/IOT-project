# E2E Test Suite Report — IOT Drone Station v2 (Track A)

**Agent**: `test_writer_e2e_v2` (Roles: Specialist, QA)  
**Date**: 2026-09-13  
**Target Specification**: `prompt-du-an-drone-v2.md` Section 12 & Table 12.1  
**Test Suite Path**: `/home/pnt/IOT/tests/`  
**Test Runner**: `/home/pnt/IOT/tests/ssh_test_runner.py`  

---

## 1. Executive Summary

We have built a comprehensive, production-grade automated end-to-end test suite covering all 16 scenarios specified in Table 12.1 of `prompt-du-an-drone-v2.md`.

The test suite supports dual-mode execution:
1. **Bench Mode (`--mode=bench`)**: An isolated, 100% reliable local test environment utilizing a virtual serial PTY (`MockESP32Serial`), an embedded lightweight HTTP MOD server (`MockMODServer`), and a mock GCS server. It runs all 16 scenarios in **0.35 seconds with a 100% pass rate (16/16 Passed)**.
2. **Remote Mode (`--mode=remote`)**: Connects over SSH (`paramiko`) to the live Raspberry Pi 5 (`192.168.1.118:22`, user: `pi5`) and exercises the live system endpoints. On live hardware, **11 of 16 scenarios PASSED** (verifying live MJPEG 1080p 30fps webcam streaming, live Argon2id 3-layer auth, dynamic PID tuning read/write, no-fly zone CRUD and geofence engine update, MOD flight permission requests, and serial JSONL communications).

The 5 remote failures on the live Pi5 uncovered genuine backend implementation defects and missing routes (pending Milestones M3/M4), which have been documented and escalated.

---

## 2. Table 12.1 Scenario Implementation Summary

| # | Scenario | File | Subsystem | Bench | Remote | Description & Assertion Integrity |
|---|---|---|---|:---:|:---:|---|
| 1 | ESP32 AP + captive portal | `tests/test_scenario_01_wifi.py` | ESP32 Provisioning | PASS | PASS | Asserts captive portal HTTP response, credential submission, and Pi5 Wi-Fi connection. |
| 2 | Pi5 online after provisioning | `tests/test_scenario_02_pi5_online.py` | Pi5 Networking | PASS | PASS | Asserts `/api/v1/health` status `ok`, network interface state, and station ID. |
| 3 | Serial JSONL Pi5 ⇄ ESP32 | `tests/test_scenario_03_serial_jsonl.py` | Serial Protocol | PASS | PASS | Bidirectional transmission on PTY/serial, validates command ACK, tests malformed line recovery. |
| 4 | Registration + Email OTP + 2FA TOTP | `tests/test_scenario_04_auth.py` | RBAC & 3-Layer Auth | PASS | FAIL | Tests user registration, OTP email verification, TOTP generation, active vs pending roles. |
| 5 | Admin forced email update + OTP | `tests/test_scenario_05_admin_forced_setup.py` | Default Admin Lock | PASS | PASS | Asserts default admin is required to complete email update & OTP setup before full API access. |
| 6 | Mandatory firmware flash | `tests/test_scenario_06_mandatory_firmware.py` | Flight Gatekeeper | PASS | FAIL | Asserts flight control endpoints are blocked until initial firmware flashing is complete. |
| 7 | Camera streaming | `tests/test_scenario_07_camera.py` | Webcam MJPEG | PASS | PASS | Asserts MJPEG multipart stream (`/api/v1/camera/stream`) receives valid JPEG frame headers at 30fps FHD. |
| 8 | Telemetry 3D (RPY + LiDAR) | `tests/test_scenario_08_telemetry_lidar.py` | WebSocket / Serial | PASS | PASS | Asserts ingestion of Roll, Pitch, Yaw attitude and LiDAR ground distance. |
| 9 | PID tuning read/write | `tests/test_scenario_09_pid_tuning.py` | Stabilization | PASS | PASS | Reads current PID, updates values via `/api/v1/drone/parameters`, verifies persistence roundtrip. |
| 10 | MOD flight request & anti-replay | `tests/test_scenario_10_mod_request.py` | Military Clearance | PASS | PASS | Submits GPS center, time window, pilot license; validates nonce and timestamp anti-replay rules. |
| 11 | MOD permit approval (1km zone) | `tests/test_scenario_11_mod_approval_zone.py` | Geodesic 1km Zone | PASS | PASS | MOD Admin approves request, generates 64-vertex geodesic circle of radius 1000m. |
| 12 | Flight window expiration | `tests/test_scenario_12_flight_window_expiry.py` | Flight Window Lock | PASS | FAIL | Asserts permit state reverts to NONE after window expiry and locks ARM command. |
| 13 | ARM lock failsafe | `tests/test_scenario_13_arm_failsafe.py` | Arming Interlock | PASS | FAIL | Asserts ARM command returns 403 Forbidden without permit, outside 1km, or outside window. |
| 14 | Firmware management | `tests/test_scenario_14_firmware_mgmt.py` | Firmware Pipeline | PASS | FAIL | Asserts firmware binary upload, SHA-256 integrity check, version listing, and deletion. |
| 15 | MOD registration approval | `tests/test_scenario_15_mod_auth_approval.py` | MOD RBAC | PASS | PASS | New MOD officer account stays PENDING until approved by MOD Admin. |
| 16 | Draw & delete no-fly zones | `tests/test_scenario_16_geofence_zones.py` | Geofence Engine | PASS | PASS | Creates complex 8-vertex polygon zone, asserts containment test, deletes zone and verifies update. |

---

## 3. Discovered Implementation Defects & Escalations

1. **Local Repository SyntaxError in `backend/app/main.py`**:
   - Lines 68 and 147 contain syntax errors that prevent importing or running local backend tests.
   - Escalate to: Backend Implementation Specialist.

2. **Runtime `AttributeError` in `/opt/drone-web-ui/backend/app/auth.py` on Pi5**:
   - In `register_step2_otp`: `challenge.get("attempts", 0)` is called on a `sqlite3.Row` object, triggering an `AttributeError` and causing HTTP 500 during registration Step 2.
   - Fix: Use `challenge["attempts"]` or `dict(challenge).get("attempts", 0)`.
   - Escalate to: Backend Implementation Specialist.

3. **Pending Routes on Pi5 Production Service (Milestones M3/M4)**:
   - `/api/v1/commands/arm` returns 405 Method Not Allowed.
   - `/api/v1/firmware/*` returns 405 Method Not Allowed.
   - Escalate to: Flight Control & Firmware Specialist.

4. **Geofence API Role Security**:
   - `POST /api/v1/geofence/zones` on Pi5 strictly enforces role `defense` (requiring user `defense` / `Defense123!`), returning 403 for `admin`. Test suite has been updated to handle role credentials appropriately.

---

## 4. Verification Instructions

To execute the test suite:

```bash
# Bench Mode (100% Pass in 0.35s)
python3 tests/ssh_test_runner.py --mode=bench

# Remote SSH Mode against Pi5
python3 tests/ssh_test_runner.py --mode=remote --host 192.168.1.118 --user pi5 --password 123456
```

Output reports:
- Machine Report: `tests/ssh_test_report.json`
- Human Report: `TEST_REPORT.md`
- Readiness Summary: `TEST_READY.md`
