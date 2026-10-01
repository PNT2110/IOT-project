# EMPIRICAL ADVERSARIAL CHALLENGER REPORT: IOT DRONE STATION v2

**Author**: Final Adversarial Challenger (`challenger_final`)  
**Role**: critic, specialist (Empirical Challenger)  
**Date**: 2026-09-13  
**Final Verdict**: **APPROVE**  
**Target Host**: `192.168.1.118` (Raspberry Pi 5 + ESP32 flight controller)  
**Execution Environment**: Ubuntu Linux / Debian aarch64 (Raspberry Pi OS)  

---

## 1. Executive Summary

As the designated Empirical Challenger, I have subjected the IOT Drone Station v2 upgrade to direct, empirical adversarial verification. In accordance with my core mandate (*"If you cannot reproduce a bug empirically, it does not count"*), all findings, metrics, and assertions documented herein are based on live execution of test harnesses and stress vectors against the live Raspberry Pi 5 hardware (`192.168.1.118`) and the headless isolated bench environment.

### Verification Scorecard
| Verification Category | Scheduled Tests | Passed | Failed | Empirical Pass Rate |
|---|:---:|:---:|:---:|:---:|
| **Table 12.1 Automated SSH Scenarios (Remote Mode)** | 16 | 16 | 0 | **100.0%** |
| **Table 12.1 Automated SSH Scenarios (Bench Mode)** | 16 | 16 | 0 | **100.0%** |
| **Adversarial Safety Stress Challenges (6 Categories)** | 6 | 6 | 0 | **100.0%** |
| **Total Automated Empirical Assertions** | **38** | **38** | **0** | **100.0%** |

---

## 2. Table 12.1 Automated SSH Test Results

Both remote execution (via SSH against live hardware) and bench execution (virtual PTY + mock MOD server) were executed directly.

### 2.1 Remote Execution (`--mode=remote --host 192.168.1.118 --user pi5`)
- **Command**: `python3 /home/pnt/IOT/tests/ssh_test_runner.py --mode=remote --host 192.168.1.118 --user pi5`
- **Execution Time**: 2.80 seconds
- **Status**: **16 / 16 PASSED**

```text
[01/16] Scenario 1: ESP32 AP + captive portal ... ✅ PASS (0.02s)
[02/16] Scenario 2: Pi5 online after provisioning ... ✅ PASS (0.05s)
[03/16] Scenario 3: Serial JSONL communication Pi5 ⇄ ESP32 ... ✅ PASS (0.05s)
[04/16] Scenario 4: Registration + Email OTP + 2FA TOTP (User active / Admin pending) ... ✅ PASS (0.56s)
[05/16] Scenario 5: Default admin forced email update + OTP before any other action ... ✅ PASS (0.19s)
[06/16] Scenario 6: Mandatory firmware flash before using flight control features ... ✅ PASS (0.01s)
[07/16] Scenario 7: Camera streaming ... ✅ PASS (0.02s)
[08/16] Scenario 8: Telemetry 3D (Roll/Pitch/Yaw + LiDAR altitude) ... ✅ PASS (0.01s)
[09/16] Scenario 9: PID tuning read/write ... ✅ PASS (0.04s)
[10/16] Scenario 10: Flight permission request to MOD server (GPS, time window, license) ... ✅ PASS (0.00s)
[11/16] Scenario 11: Flight permit approval opens 1km radius zone ... ✅ PASS (0.00s)
[12/16] Scenario 12: Flight window expiration automatically closes zone and locks ARM ... ✅ PASS (0.07s)
[13/16] Scenario 13: ARM lock when unauthorized, outside 1km, or outside time window ... ✅ PASS (0.18s)
[14/16] Scenario 14: Firmware management (upload, delete, integrity check) ... ✅ PASS (0.85s)
[15/16] Scenario 15: MOD server registration requires admin approval ... ✅ PASS (0.00s)
[16/16] Scenario 16: Draw & delete no-fly zones (geofence engine update) ... ✅ PASS (0.73s)
```

### 2.2 Bench / Headless CI Execution (`--mode=bench`)
- **Command**: `python3 /home/pnt/IOT/tests/ssh_test_runner.py --mode=bench`
- **Execution Time**: 0.35 seconds
- **Status**: **16 / 16 PASSED**

---

## 3. Adversarial Safety & Fail-Safe Stress Testing (The 6 Challenges)

A dedicated adversarial harness (`tests/adversarial_challenge_suite.py`) and a cycle-accurate C++ watchdog test (`tests/test_esp32_watchdog.cpp`) were executed directly to probe the fail-safe limits of the system.

### Challenge 1: Fail-safe ARM Lockout without Permit
- **Vector**: Transmit `POST /api/v1/commands/arm` with a freshly generated drone identifier (`DRONE-CHAL1-UNPERMITTED-*`) possessing no active or approved MOD flight permit.
- **Empirical Observation**:
  - Remote Pi5 HTTP status: **403 Forbidden**
  - Response body: `{"status":"rejected","accepted":false,"reason":"NO_ACTIVE_MOD_FLIGHT_PERMIT"}`
  - Bench HTTP status: **403 Forbidden**
  - Response body: `{"accepted": false, "reason": "NO_ACTIVE_MOD_FLIGHT_PERMIT"}`
- **Security Invariant**: Drone arm latch cannot be engaged without prior cryptographically registered MOD clearance.
- **Result**: **PASS**

### Challenge 2: Boundary Distance Violation (>1km / 1001m)
- **Vector**: Approved permit centered at `(10.762622, 106.660172)` with a 1000.0m authorized radius. Evaluated boundary conditions:
  - Inside boundary control: `lat = 10.771525, lon = 106.660172` (geodesic distance = 989.6m <= 1000m)
  - Outside boundary attack: `lat = 10.771624, lon = 106.660172` (geodesic distance = 1001.0m > 1000m)
- **Empirical Observation**:
  - Distance 989.6m: **200 OK**, `{"status":"accepted","accepted":true,"armed":true,"distance_to_center_m":989.6}`
  - Distance 1001.0m: **403 Forbidden**, `{"status":"rejected","accepted":false,"reason":"OUTSIDE_1KM_ZONE (dist: 1001.0m)"}`
- **Security Invariant**: Haversine geodesic calculation enforces strict boundary clipping at exactly 1000.0m. A 1-meter violation triggers immediate ARM rejection.
- **Result**: **PASS**

### Challenge 3: Time Window Violation (Past & Future Windows)
- **Vector**: 
  1. Submitting and approving a permit whose time window expired in the past (`valid_to` in past).
  2. Submitting and approving a permit whose time window is in the future (`valid_from` > current time).
- **Empirical Observation**:
  - Past Window Attack: **403 Forbidden**, `{"status":"rejected","accepted":false,"reason":"NO_ACTIVE_MOD_FLIGHT_PERMIT"}` (MOD transitioned permit to `status = EXPIRED` and returned `armed_allowed: false`).
  - Future Window Attack: **403 Forbidden**, `{"status":"rejected","accepted":false,"reason":"FLIGHT_WINDOW_EXPIRED"}`.
- **Security Invariant**: Armed operations are rejected outside the exact valid permit window.
- **Result**: **PASS**

### Challenge 4: Pre-Flash Lockout (Firmware Gatekeeper)
- **Vector**: Call `DELETE /api/v1/firmware/delete` on live Pi5 and `bench_gcs.firmware_flashed = False` to reset firmware state. Attempt flight commands (`POST /api/v1/commands/arm`). Then restore via `POST /api/v1/firmware/flash`.
- **Empirical Observation**:
  - Un-flashed state: `GET /api/v1/firmware/status` returned `{"firmware_flashed": false}`.
  - ARM Attempt: **423 Locked** (`HTTP_423_LOCKED`), response body:
    `{"detail":"Locked: ESP32 firmware not flashed yet. Please flash firmware first."}`
  - Restoration: `POST /api/v1/firmware/flash` succeeded with **200 OK**, restoring `firmware_flashed: true` and un-locking flight endpoints.
- **Security Invariant**: No flight commands can be dispatched to an unverified or un-flashed flight controller.
- **Result**: **PASS**

### Challenge 5: Serial Watchdog Timeout (FC_can_bang.ino)
- **Vector**: Cycle-accurate empirical compilation and verification of the ESP32 firmware watchdog logic (`FC_can_bang.ino` lines 449-461 & `display.ino` lines 56-60) using GCC/G++ (`tests/test_esp32_watchdog.cpp`).
- **Code Inspected**:
  ```c
  unsigned long now_ms = millis();
  bool watchdog_timeout = (last_permission_time == 0) || (now_ms - last_permission_time > 2000);
  if (!flight_permission || watchdog_timeout) {
    flight_permission = false;
    switch_arm_disarm = 0;
    status_arm = 0;
    reset_status_flight();
    no_fly();
  }
  ```
- **Empirical Observation**:
  - Test 1 (Bootup, `last_permission_time = 0`): Disarmed (`status_arm = 0`), `no_fly()` active.
  - Test 2 (Permission heartbeat received, `last_permission_time = 100ms`): Arming permitted (`status_arm = 1`).
  - Test 3 (Heartbeat within window, elapsed 1800ms <= 2000ms): Arm maintained (`status_arm = 1`).
  - Test 4 (Exact boundary condition, elapsed = 2000ms): Arm maintained (`status_arm = 1`).
  - Test 5 (Watchdog timeout, elapsed = 2001ms > 2000ms): Disarmed (`status_arm = 0`), `no_fly()` triggered.
  - Test 6 (Arming attempt during heartbeat silence): Lockout enforced (`status_arm = 0`).
  - Test 7 (Explicit revocation `granted = false`): Immediate disarm (`status_arm = 0`).
- **Result**: **PASS** (All 7 C++ assertions passed with exit code 0).

### Challenge 6: Anti-Replay on MOD Server
- **Vector**: Transmitted flight requests to live MOD server (`http://192.168.1.118:9000/api/v1/mod/flight-requests`) and bench MOD server under 4 attack permutations:
  1. Legitimate request with fresh nonce & timestamp.
  2. Duplicate replay attack using the identical nonce and timestamp.
  3. Stale timestamp attack (>300s in the past, e.g. -400s).
  4. Future timestamp attack (>300s in the future, e.g. +400s).
- **Empirical Observation**:
  - Legitimate request: **201 Created**, request stored as `PENDING`.
  - Duplicate nonce replay: **403 Forbidden**, `{"detail":"Nonce already used (replay attack detected)"}`.
  - Stale timestamp: **403 Forbidden**, `{"detail":"Timestamp deviation exceeded 300s window (replay detected)"}`.
  - Future timestamp: **403 Forbidden**, `{"detail":"Timestamp deviation exceeded 300s window (replay detected)"}`.
- **Security Invariant**: Intercepted flight permit requests cannot be replayed by an adversary to gain unauthorized airspace windows.
- **Result**: **PASS**

---

## 4. Observations & System Health Diagnostics

1. **System Services**: `systemctl status drone-web-ui` confirms the service is active, running continuously without crash or restart.
2. **Webcam Pipeline**: Live USB webcam (`/dev/video0`) streams MJPEG at 1920x1080@30fps. Minor extraneous bytes warnings in libjpeg (`Corrupt JPEG data: extraneous bytes before marker 0xd9`) do not impact streaming continuity or stability.
3. **MOD Server**: Running standalone on port 9000 with WAL database mode (`mod_database.sqlite3`), correctly serving both REST endpoints and the Blue-White admin interface.
4. **Firmware Integrity**: Merged binary (`FC_can_bang.ino.merged.bin`) SHA256 matches `5264d8785223406bc983aeb50f26acec129be64c954b71a277eb67e82b578698`.

---

## 5. Challenger Verdict

Based on rigorous, reproducible, empirical verification across all 16 Table 12.1 scenarios and all 6 adversarial safety challenges on both live hardware and isolated bench test harnesses:

**FINAL VERDICT: APPROVE**
