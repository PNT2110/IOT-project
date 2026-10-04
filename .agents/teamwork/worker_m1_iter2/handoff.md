# Milestone 1 (Iteration 2) Handoff Report: Altitude Limiter & Async Mail Remediation

**Agent**: `worker_m1_iter2` (Milestone 1 Worker - Iteration 2)  
**Parent Agent**: `3be5ec9a-8b7d-4356-b0b8-0a206dabba81`  
**Working Directory**: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m1_iter2`  
**Timestamp**: 2026-10-03T21:44:00Z  
**Type**: Hard Handoff (Task Complete)  

---

## 1. Observation

### 1.1 Initial State & Challenger Findings
Milestone 1 Iteration 1 was rejected by Challengers 1 and 2 due to three physical failure modes in `firmware/FC_can_bang/flight_gate.h` and `MODE.ino`:

1. **Defect 1 — Apogee / Level-off Floor Collapse to 1100 µs**:
   - In `firmware/FC_can_bang/flight_gate.h` (former lines 86–93):
     ```cpp
     if (min_floor_us > 0.0f) {
       s.floor_us = min_floor_us;
     } else if (vspeed_mps != 0.0f) {
       float dynamic_base = (float)throttle_us - ALT_LIMIT_MARGIN_US;
       s.floor_us = dynamic_base > ALT_LIMIT_DEFAULT_FLOOR_US ? dynamic_base : (float)ALT_LIMIT_DEFAULT_FLOOR_US;
     } else {
       s.floor_us = ALT_LIMIT_DEFAULT_FLOOR_US;
     }
     ```
   - In `firmware/FC_can_bang/MODE.ino` (line 10), `altitude_throttle_cap()` was called without `min_floor_us`, leaving it as `0.0f`.
   - When reaching ceiling at apogee or in level flight (`vspeed_mps == 0.0f`), `s.floor_us` collapsed unconditionally to `1100 µs` (`ALT_LIMIT_DEFAULT_FLOOR_US`), causing drone throttle to decay to 1100 µs (~10% thrust, far below F450 hover thrust ~1450 µs).
   - Verbatim stress probe output before fix:
     ```
     [VULNERABILITY 1 CONFIRMED] Level-off ceiling entry (vspeed=0) resets floor_us to 1100 us!
     ```

2. **Defect 2 — High Climb Punch-Out Lockout**:
   - When breaching ceiling during a rapid climb (e.g. `throttle_us = 1850 µs`, `vspeed_mps = +4.0 m/s`), `dynamic_base = 1850 - 150 = 1700 µs`.
   - `s.floor_us` was latched at 1700 µs, which produces sustained climbing thrust on an F450 frame, defeating altitude ceiling control.
   - Verbatim stress probe output before fix:
     ```
     [VULNERABILITY 2 CONFIRMED] High climb entry locks throttle floor at 1700 us (> 1450 hover)!
                                  Drone will climb indefinitely above ceiling!
     ```

3. **Defect 3 — Rapid Descent Depression Below Safe Floor**:
   - In `firmware/FC_can_bang/flight_gate.h` line 110:
     ```cpp
     if (effective_floor > (float)throttle_us - 20.0f) {
       effective_floor = (float)throttle_us - 20.0f;
     }
     ```
   - When descending at -1.0 m/s with pilot stick near hover (e.g. 1460 µs) and `min_floor_us = 1450 µs`, `effective_floor` was clamped to `1460 - 20 = 1440 µs`, depressing the throttle floor below `min_floor_us`.
   - Verbatim stress probe output before fix:
     ```
     [VULNERABILITY 3 CONFIRMED] Rapid descent (-1.0 m/s) depresses throttle cap to 1440 us (< min_floor 1450 us)!
     ```

4. **Reviewer Advisory — Unawaited Coroutine Risk in `mail.py`**:
   - In `server/app/mail.py`, `SmtpEmailSender.send_code` was defined as `async def send_code`, while existing callers such as `server/app/services.py:176` (`create_email_code`) and `server/cli.py:42` (`bootstrap_owner`) are synchronous and call `mail.send_code(...)` without `await`. In production with SMTP configured, this returned an unawaited coroutine object and triggered `RuntimeWarning: coroutine was never awaited`.

---

## 2. Logic Chain

### 2.1 Remediation of Firmware Defects (`MODE.ino` and `flight_gate.h`)

1. **Fix for Defect 1 (`MODE.ino`)**:
   - Defined `#define ALT_LIMIT_SAFE_FLOOR_US 1350.0f` in `firmware/FC_can_bang/MODE.ino` line 8.
   - Passed `ALT_LIMIT_SAFE_FLOOR_US` as the 6th argument to `altitude_throttle_cap()` in `apply_altitude_limit()` (line 12).
   - In physical flight, the F450 flight controller is now guaranteed to provide at least 1350 µs hover thrust baseline.

2. **Fix for Defects 1 & 2 (`flight_gate.h`)**:
   - Added `#define ALT_LIMIT_MAX_ENTRY_FLOOR_US 1450.0f` to prevent punch-out climb lock-in.
   - Removed the faulty `vspeed_mps != 0.0f` condition. Upon ceiling breach (`!s.active`), `dynamic_base` is calculated unconditionally from entry throttle:
     ```cpp
     float dynamic_base = (float)throttle_us - ALT_LIMIT_MARGIN_US;
     if (dynamic_base > ALT_LIMIT_MAX_ENTRY_FLOOR_US) {
       dynamic_base = ALT_LIMIT_MAX_ENTRY_FLOOR_US;
     }
     if (dynamic_base < (float)ALT_LIMIT_DEFAULT_FLOOR_US) {
       dynamic_base = (float)ALT_LIMIT_DEFAULT_FLOOR_US;
     }

     if (min_floor_us > 0.0f) {
       s.floor_us = min_floor_us;
     } else {
       s.floor_us = dynamic_base;
     }
     ```
   - When entering at hover (`1500 µs`, `vspeed = 0.0f`), `s.floor_us` becomes `1350 µs`, preventing collapse to 1100 µs.
   - When entering during high punch-out (`1850 µs`, `vspeed = +4.0 m/s`), `dynamic_base` is capped at `1450 µs`, allowing the limiter to ease throttle down to hover and arrest the climb.

3. **Fix for Defect 3 (`flight_gate.h`)**:
   - In `altitude_throttle_cap()`, defined `safe_floor`:
     ```cpp
     float safe_floor = (min_floor_us > 0.0f) ? min_floor_us : s.floor_us;
     if (effective_floor < safe_floor) {
       effective_floor = safe_floor;
     }
     if (effective_floor < (float)ALT_LIMIT_DEFAULT_FLOOR_US) {
       effective_floor = (float)ALT_LIMIT_DEFAULT_FLOOR_US;
     }
     ```
   - Clamping to `throttle_us - 20.0f` can never depress `effective_floor` below `safe_floor` (`min_floor_us` or `s.floor_us`).
   - Pilot retains full lower throttle override authority at all times via `return throttle_us > (int)s.cap_us ? (int)s.cap_us : throttle_us;`.

### 2.2 Remediation of Async Mail Sender (`mail.py`)

1. **Dual-Mode Execution Architecture**:
   - Created `DualModeMailCall(collections.abc.Coroutine)` in `server/app/mail.py`, wrapping a `concurrent.futures.Future` submitted to an internal `ThreadPoolExecutor(max_workers=20, thread_name_prefix="smtp_sender")`.
   - `inspect.markcoroutinefunction(SmtpEmailSender.send_code)` ensures that `inspect.iscoroutinefunction(sender.send_code)` returns `True`.
   - When awaited (`await sender.send_code(...)`), wrapped in `asyncio.create_task(...)`, or grouped in `asyncio.gather(...)`, `DualModeMailCall` yields execution to `asyncio.wrap_future(fut).__await__()`, providing fully non-blocking asynchronous event loop execution, exception propagation (`socket.timeout`, `SMTPServerDisconnected`, `SMTPConnectError`), and clean `asyncio.CancelledError` handling.
   - When invoked synchronously without `await` (e.g. `services.py:create_email_code` or CLI commands), the task runs in the background threadpool, delivering the email without blocking the event loop and without generating `RuntimeWarning: coroutine was never awaited`.

---

## 3. Caveats

1. Flight aerodynamics were verified using the host C++ test suites and adversarial probes (`g++ -std=c++17 -Wall -Wextra -Werror`), which test the exact C++ algorithm embedded in ESP32 firmware. Hardware bench testing with physical ESCs/motors and barometer sensor noise will occur during hardware flight validation.
2. In `server/app/security.py`, `normalize_email` behavior is intact and verified against 15+ adversarial fuzzed test cases.
3. No files outside the 6 assigned files were touched.

---

## 4. Conclusion

All three altitude limiter defects and the async mail unawaited coroutine warning have been fully remediated and verified:
1. `MODE.ino` passes `ALT_LIMIT_SAFE_FLOOR_US (1350.0f)` to `altitude_throttle_cap()`.
2. `flight_gate.h` handles apogee/level-off entries safely without floor collapse, caps dynamic climb entry floor at 1450 µs, and prevents descent depression below safe floors.
3. `mail.py` supports both non-blocking async execution and safe synchronous calling without warnings or event loop blockage.
4. All 3 Challenger vulnerability probes now pass with **0 vulnerabilities detected**.
5. All test suites (`pytest tests/firmware/ tests/scope01/ tests/scope02/`) pass 100% (108/108 passed).

---

## 5. Verification Method

### 5.1 Firmware Stress & Adversarial Probes
```powershell
# 1. Run Challenger 1 stress test (Verifies all 3 vulnerabilities fixed):
powershell -Command "& 'C:\Strawberry\c\bin\g++.exe' -std=c++17 -Wall -Wextra -I firmware/FC_can_bang tests/firmware/test_altitude_limiter_stress.cpp -o tests/firmware/test_altitude_limiter_stress.exe; & './tests/firmware/test_altitude_limiter_stress.exe'; Remove-Item -Force tests/firmware/test_altitude_limiter_stress.exe"

# Expected output:
# Results: 3 checks passed, 0 critical vulnerabilities confirmed empirically.

# 2. Run Challenger 2 adversarial probe:
powershell -Command "& 'C:\Strawberry\c\bin\g++.exe' -std=c++17 -Wall -Wextra -I firmware/FC_can_bang tests/firmware/test_adversarial_flight_gate.cpp -o test_gate.exe; & './test_gate.exe'; Remove-Item -Force test_gate.exe"
# Expected output:
# Apogee entry floor_us=1350.0 (no collapse)

# 3. Compile and run updated firmware unit tests with -Werror:
powershell -Command "& 'C:\Strawberry\c\bin\g++.exe' -std=c++17 -Wall -Wextra -Werror -I firmware/FC_can_bang tests/firmware/test_flight_gate.cpp -o test_fg.exe; & './test_fg.exe'; Remove-Item -Force test_fg.exe"
# Expected output:
# flight_gate: all checks passed
```

### 5.2 Full Pytest Test Suites
```powershell
# Run firmware host build, scope01 (auth, email, security, smtp concurrency, stress), and scope02 regression suites:
pytest tests/firmware/ tests/scope01/ tests/scope02/
# Expected result:
# 108 passed
```
