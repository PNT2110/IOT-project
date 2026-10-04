# Dispatch Task: Milestone 1 — Core Bug Fixes across Tiers

## Identity
- Role: Milestone 1 Worker
- TypeName: teamwork_preview_worker
- Working Directory: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m1
- Parent Conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81

## Authoritative Requirements & References
- Requirements: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md`
- Project Spec: `c:\Users\pnt21\Desktop\IOT\PROJECT.md`
- Firmware Survey Report: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1\handoff.md`
- Server Backend Survey Report: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_2\handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive Write Ownership
You exclusively own and may edit ONLY the following files:
1. `firmware/FC_can_bang/flight_gate.h`
2. `firmware/FC_can_bang/MODE.ino`
3. `server/app/mail.py`
4. `server/app/security.py`
5. `tests/firmware/test_flight_gate.cpp` (and any new firmware test files under `tests/firmware/`)
6. New unit test file `tests/scope01/test_email_normalization.py` (or additions to `tests/scope01/`)
DO NOT modify any other files.

## Detailed Tasks
1. **Bug 1: Dynamic Altitude Limiter Floor in `firmware/FC_can_bang/flight_gate.h`**:
   - Update `altitude_throttle_cap()` and `AltLimiter` struct per `PROJECT.md § Interface Contracts` and `explorer_survey_1/handoff.md`.
   - Prevent uncontrolled descent on heavily loaded F450 drone by introducing dynamic floor accounting for current flight state (entry/latch throttle and/or vertical speed dampening from barometer) rather than a hardcoded 1100 µs floor.
   - Preserve default arguments/behavior so existing tests in `test_flight_gate.cpp` continue to pass.
   - Update `firmware/FC_can_bang/MODE.ino` to pass vertical speed (`baro_vspeed_mps`) into `altitude_throttle_cap()` when barometer is available.
   - Add new test cases in `tests/firmware/test_flight_gate.cpp` verifying that dynamic floor protects against uncontrolled descent.
   - Run firmware tests via `pytest tests/firmware/`.
2. **Bug 2: Non-Blocking Email Sending in `server/app/mail.py`**:
   - Update `SmtpEmailSender.send_code()` so that blocking synchronous SMTP calls do not block the asyncio event loop.
   - Wrap the network call in `asyncio.to_thread()` or implement non-blocking coroutine pattern while ensuring backwards compatibility with synchronous callers and `FakeEmailSender`.
   - Verify with existing tests in `tests/scope01/` and `tests/scope02/`.
3. **Bug 3: Email Normalization in `server/app/security.py`**:
   - Update `normalize_email()` to strip periods (`.`) in the local part for Gmail-family domains (`gmail.com`, `googlemail.com`) and strip subaddresses (`+tag`).
   - Example: `john.doe+test@gmail.com` must normalize to `johndoe@gmail.com`.
   - Add comprehensive pytest tests in `tests/scope01/test_email_normalization.py` proving that aliased emails normalize identically.
   - Run `pytest tests/scope01/` and ensure all pass.

## Verification Requirements
- Run `pytest tests/firmware/` and `pytest tests/scope01/`.
- Ensure all tests pass with 0 errors.
- Document exact commands and outputs in `handoff.md`.


## 2026-10-03T20:54:53Z
You are worker_m1, the Milestone 1 Worker for Core Bug Fixes across Tiers.
Your working directory is: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m1
The authoritative requirements are in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md
The project specification is in: c:\Users\pnt21\Desktop\IOT\PROJECT.md
The detailed dispatch instructions are in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m1\DISPATCH.md
Survey handoff reports with exact code analysis are in:
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1\handoff.md (Firmware Bug 1)
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_2\handoff.md (Server Bugs 2 & 3)

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You exclusively own:
- firmware/FC_can_bang/flight_gate.h
- firmware/FC_can_bang/MODE.ino
- server/app/mail.py
- server/app/security.py
- tests/firmware/test_flight_gate.cpp (and any new firmware test files under tests/firmware/)
- tests/scope01/test_email_normalization.py (and additions to tests/scope01/)

Implement Bug 1 (dynamic altitude limiter floor), Bug 2 (non-blocking SMTP email sender), and Bug 3 (RFC/Gmail email normalization).
Run pytest tests/firmware/ and pytest tests/scope01/.
Write your comprehensive completion report to c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m1\handoff.md, update progress.md, and send a completion message to parent orchestrator (conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81).
