# Dispatch Task: Milestone 1 (Iteration 2) — Fix Altitude Limiter Vulnerabilities

## Identity
- Role: Milestone 1 Worker (Iteration 2)
- TypeName: teamwork_preview_worker
- Working Directory: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m1_iter2
- Parent Conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81

## Authoritative Requirements & References
- Requirements: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md`
- Project Spec: `c:\Users\pnt21\Desktop\IOT\PROJECT.md`
- Gate Status & Failure Reason: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\orchestrator_1\GATE_STATUS.md`
- Challenger 1 Report: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m1_1\handoff.md`
- Challenger 2 Report: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m1_2\handoff.md`
- Reviewer 1 Report: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\reviewer_m1_1\handoff.md`
- Reviewer 2 Report: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\reviewer_m1_2\handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive Write Ownership
You exclusively own and may edit ONLY the following files:
1. `firmware/FC_can_bang/flight_gate.h`
2. `firmware/FC_can_bang/MODE.ino`
3. `server/app/mail.py`
4. `server/app/security.py`
5. `tests/firmware/test_flight_gate.cpp` (and other test files in `tests/firmware/`)
6. `tests/scope01/test_email_normalization.py`

## Specific Defect Remediation Instructions
Milestone 1 Iteration 1 was REJECTED by Challengers 1 and 2 due to 3 critical physical failure modes in `flight_gate.h` and `MODE.ino`:

1. **Defect 1 (Apogee / Level-off Floor Collapse to 1100 µs)**:
   - Root Cause: In `flight_gate.h`, line 88 checks `else if (vspeed_mps != 0.0f)`. When entering altitude limiting at level-off or apogee (`vspeed_mps == 0.0f`), and `min_floor_us` is omitted (defaulting to `0.0f`), the condition is false. The code takes `else { s.floor_us = ALT_LIMIT_DEFAULT_FLOOR_US; }` (1100 µs). If hovering above ceiling, throttle cap decays to 1100 µs (~10% throttle, far below F450 hover thrust ~1450 µs), causing severe free-fall.
   - Fix in `MODE.ino`: In line 10, pass an explicit safe hover floor constant for F450:
     ```cpp
     #define ALT_LIMIT_SAFE_FLOOR_US 1350.0f
     throttle_smoot = altitude_throttle_cap(alt_limiter, Altitude_barometer - arm_ground_alt, max_altitude_m, (int)throttle_smoot, baro_vspeed_mps, ALT_LIMIT_SAFE_FLOOR_US);
     ```
   - Fix in `flight_gate.h`: Ensure that when `min_floor_us > 0.0f`, `s.floor_us` is NEVER set below `min_floor_us`. Even when `min_floor_us == 0.0f`, if entering at hover throttle `throttle_us`, ensure `s.floor_us` does not collapse unconditionally when `vspeed_mps == 0.0f`.

2. **Defect 2 (Punch-Out Lockout)**:
   - Root Cause: If a drone enters ceiling during high climb at 1850 µs, `dynamic_base = throttle_us - 150 = 1700 µs`. A floor of 1700 µs is too high to arrest climb.
   - Fix in `flight_gate.h`: Cap the maximum entry floor at a safe upper bound (e.g. `1450.0f` or `min_floor_us > 0.0f ? min_floor_us + 100.0f : 1450.0f`), so the limiter can always ease throttle down toward hover.

3. **Defect 3 (Descent Depression Below Safe Floor)**:
   - Root Cause: In rapid descent, line 110 clamps `effective_floor` to `throttle_us - 20`, which can depress the floor below `min_floor_us`.
   - Fix in `flight_gate.h`: Ensure `effective_floor` is never depressed below `s.floor_us` or `min_floor_us` when `min_floor_us > 0.0f`.

4. **Reviewer Advisory on `mail.py`**:
   - Ensure `SmtpEmailSender.send_code` is safe when called synchronously by existing callers (e.g. `services.py:create_email_code`) without producing unawaited coroutine warnings, while maintaining non-blocking asynchronous execution on the event loop (via `asyncio.to_thread` or threadpool executor).

## Verification Requirements
- Re-run all existing test suites:
  - `pytest tests/firmware/`
  - `pytest tests/scope01/`
  - Run the challenger stress test if present: `tests/firmware/test_altitude_limiter_stress.cpp`
- Verify 100% test pass.
- Write your handoff report to `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m1_iter2\handoff.md`.


## 2026-10-03T21:22:48Z
You are worker_m1_iter2, Milestone 1 Worker (Iteration 2).
Your working directory is: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m1_iter2
The authoritative requirements are in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md
The project specification is in: c:\Users\pnt21\Desktop\IOT\PROJECT.md
The dispatch instructions and challenger reports are in:
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m1_iter2\DISPATCH.md
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m1_1\handoff.md
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m1_2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You exclusively own:
- firmware/FC_can_bang/flight_gate.h
- firmware/FC_can_bang/MODE.ino
- server/app/mail.py
- server/app/security.py
- tests/firmware/test_flight_gate.cpp (and tests/firmware/)
- tests/scope01/test_email_normalization.py

Fix the 3 altitude limiter defects identified by Challengers 1 & 2:
1. Pass ALT_LIMIT_SAFE_FLOOR_US (1350.0f) in MODE.ino line 10.
2. In flight_gate.h, ensure s.floor_us never drops below min_floor_us, and handle vspeed_mps == 0.0f level-off / apogee safely.
3. Cap dynamic entry floor at 1450.0f to prevent punch-out climb lockout.
4. Prevent effective_floor depression below min_floor_us during descent.
5. In mail.py, ensure send_code is non-blocking on the event loop while safe for synchronous callers.
Verify with pytest tests/firmware/ and pytest tests/scope01/.
Write your handoff report to c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m1_iter2\handoff.md and report completion to parent orchestrator (conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81).
