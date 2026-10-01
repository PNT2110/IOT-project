# DISPATCH — worker_remediate_5
Timestamp: 2026-09-14T03:48:00+07:00

## Identity & Role
- Agent Name: worker_remediate_5
- Archetype: teamwork_preview_worker
- Assigned Working Directory: /home/pnt/IOT/.agents/worker_remediate_5
- Parent Conversation ID: ec132afd-20fb-4e3f-8ced-f823b42ac295

## Context & Input Files
- User Request: /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (specifically request at 2026-09-13T20:45:54Z)
- Specification: /home/pnt/IOT/prompt-du-an-drone-v2.md
- Project Scope & Architecture: /home/pnt/IOT/PROJECT.md
- Previous Reviewer Audit: /home/pnt/IOT/.agents/reviewer_final/report.md
- Test Status: /home/pnt/IOT/TEST_REPORT.md
- Security Report: /home/pnt/IOT/SECURITY_RISK_REPORT_V2.md
- Assumptions: /home/pnt/IOT/ASSUMPTIONS_V2.md

## Key Constraints (CRITICAL)
- DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
- Bare-metal / systemd on Pi5 (DO NOT use Docker).
- Fail-safe ARM locking: lock ARM if MOD approval is absent/invalid, outside coordinates/time window (>1km), or invalid data. NEVER set ENABLE_REAL_FLIGHT_COMMANDS=true.
- Security hardening (R6):
  * Absolute rule: DO NOT change password of user `pi5` (must remain `123456`).
  * Absolute rule: DO NOT disable Password Authentication on Pi5.
  * Pi5 IP is `192.168.1.118`.
  * Safe SSH key setup and security vulnerability audit per item 13 with risk report.

## Objectives & Tasks
1. Code Remediation in Local Backend:
   a. Check `backend/app/main.py`: Fix any SyntaxError or signature issues (e.g. line 68 newline escape, line 147 parameters). Verify with `python3 -m py_compile backend/app/main.py`. Ensure endpoints `POST /api/v1/auth/login`, `POST /api/v1/auth/admin-force-setup`, `/api/v1/commands/arm`, `/api/v1/firmware/*` are properly mounted.
   b. Check `backend/app/auth.py`: Fix `sqlite3.Row` error (e.g. `challenge.get(...)` -> `challenge['attempts']` or `dict(challenge).get(...)`). Ensure user role is activated immediately (`approved`/`active`) upon 2FA TOTP completion, while admin role is `pending_approval`.
   c. Check `backend/tests/test_challenger_lifecycle.py`: Ensure line range check or AST check accommodates line 183 inside `open_serial_port`.
   d. Check `tests/test_scenario_04_auth.py` & `tests/test_scenario_05_admin_forced_setup.py`: Ensure strict assertions (`assert s_resp.status_code == 200` without suppressing errors; user role status assert `approved`/`active`, admin assert `pending`/`pending_approval`).
2. Synchronize & Deploy to Raspberry Pi 5 (`192.168.1.118`):
   a. Connect to `pi5@192.168.1.118` (password: `123456` or SSH key).
   b. Sync updated backend files to `/opt/drone-web-ui/backend/app/` and `/home/pi5/iot-drone/backend/app/`.
   c. Restart systemd services (`sudo systemctl restart drone-web-ui` and any related services).
   d. Verify live services and endpoints respond cleanly (curl `POST /api/v1/auth/login`, `admin-force-setup`, etc.).
3. Verification Runs:
   a. Run backend pytest suite (`/home/pnt/miniconda3/envs/antidrone/bin/pytest tests/` or active venv in `/home/pnt/IOT/backend`). All tests must pass (100%).
   b. Run automated SSH test runner against Pi5:
      `python3 tests/ssh_test_runner.py --mode=remote --host 192.168.1.118 --user pi5`
      Also run bench mode: `python3 tests/ssh_test_runner.py --mode=bench`
      Ensure all 16 scenarios pass cleanly with real assertions and logs.
4. Documentation & Handoff:
   a. Update `TEST_REPORT.md` with full 16/16 execution results and environment diagnostics.
   b. Write comprehensive `handoff.md` and `report.md` in `.agents/worker_remediate_5/`.
   c. Send completion message back to orchestrator.
