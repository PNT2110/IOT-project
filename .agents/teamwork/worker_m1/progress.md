# Progress — Milestone 1 Worker (Core Bug Fixes across Tiers)

Last visited: 2026-10-03T21:06:30Z

## Status: COMPLETED

### Task Checklist
- [x] 1. Bug 1: Firmware Altitude Limiter Dynamic Floor
  - [x] Investigate `firmware/FC_can_bang/flight_gate.h`, `MODE.ino`, `tests/firmware/test_flight_gate.cpp`
  - [x] Implement dynamic floor calculation in `flight_gate.h`
  - [x] Update `MODE.ino` to pass `baro_vspeed_mps`
  - [x] Update and expand `tests/firmware/test_flight_gate.cpp`
  - [x] Verify `pytest tests/firmware/` (2 passed in 1.25s)
- [x] 2. Bug 2: Non-blocking SMTP Email Sender in `server/app/mail.py`
  - [x] Investigate `server/app/mail.py` and its callers in `server/app/services.py` and `routers/auth.py`
  - [x] Implement non-blocking email sender using `asyncio.to_thread`
  - [x] Verify backwards compatibility with synchronous callers and test suites
- [x] 3. Bug 3: Email Normalization in `server/app/security.py`
  - [x] Investigate `normalize_email()` in `server/app/security.py`
  - [x] Implement RFC/Gmail dot-stripping and `+tag` subaddress removal
  - [x] Create `tests/scope01/test_email_normalization.py`
  - [x] Verify `pytest tests/scope01/` (59 passed in 24.8s)
- [x] 4. Final verification & handoff
  - [x] Run `pytest tests/firmware/ tests/scope01/` (61 passed in 26.25s)
  - [x] Run `pytest tests/scope02/` (28 passed in 18.92s, 0 regressions)
  - [x] Write `handoff.md`
  - [x] Send message to orchestrator
