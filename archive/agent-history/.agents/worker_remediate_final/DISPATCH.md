## 2026-09-13T13:44:24Z

You are the Remediation Worker for the IOT Drone Station v2 project upgrade.
Your working directory: /home/pnt/IOT/.agents/worker_remediate_final
User request record: /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (read section ## 2026-09-13T09:30:16Z)
Specification file: /home/pnt/IOT/prompt-du-an-drone-v2.md
Reviewer Report: /home/pnt/IOT/.agents/reviewer_final/report.md
Reviewer Handoff: /home/pnt/IOT/.agents/reviewer_final/handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Mission — Execute the 5-Point Remediation Plan:
1. Fix Backend Unit Test Line Range (`backend/tests/test_challenger_lifecycle.py:148`):
   - In `backend/tests/test_challenger_lifecycle.py`, line 148 currently asserts `assert 130 <= line <= 170`.
   - In `backend/app/serial_io.py`, `open_serial_port` spans lines 163–203. The direct instantiation at line 183 is inside the fallback block of `open_serial_port`.
   - Update line 148 to `assert 130 <= line <= 210` (or inspect enclosing function node) so `python3 -m pytest tests/` in `backend/` passes 100% cleanly.
2. Fix Test Scenario 5 Assertion (`tests/test_scenario_05_admin_forced_setup.py`):
   - Remove the `else:` branch that swallows non-200 responses.
   - Enforce strict `assert s_resp.status_code == 200` on `/api/v1/auth/admin-force-setup`.
3. Fix User Immediate Activation in Auth & Test Scenario 4:
   - In `backend/app/auth.py` and `backend/app/main.py`, ensure that when a user registers with `role == 'user'`, their account becomes `approved` (active) immediately upon 2FA TOTP verification, while `role == 'admin'` remains `pending_approval` until approved by default admin.
   - In `tests/test_scenario_04_auth.py`, strictly assert `assert user_status in ("approved", "active")` and `assert admin_status in ("pending", "pending_approval")`.
4. Synchronize Backend to Raspberry Pi 5 (`192.168.1.118`) & Fix Live Login:
   - Copy `/home/pnt/IOT/backend/app/main.py` and `/home/pnt/IOT/backend/app/auth.py` and `/home/pnt/IOT/backend/app/firmware.py` directly to `/opt/drone-web-ui/backend/app/` on Pi5.
   - Restart the service: `ssh pi5@192.168.1.118 "sudo systemctl restart drone-web-ui"`.
   - Verify with curl on Pi5: `curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"Admin123!"}'` (or test user) returns valid response (NOT 405 Method Not Allowed).
   - Verify `/api/v1/auth/admin-force-setup` is reachable on Pi5.
5. Verification:
   - Run `python3 tests/ssh_test_runner.py --mode=remote --host 192.168.1.118 --user pi5` and verify legitimate 16/16 PASS with zero bypassed assertions.
   - Run backend tests: `cd backend && PYTHONPATH=. /home/pnt/miniconda3/envs/antidrone/bin/pytest tests/` and verify 100% PASS.
   - Update `/home/pnt/IOT/TEST_REPORT.md` with the verified output.

Deliverables:
- Code fixes applied in local repo and on Pi5
- Passing test logs
- Report in `/home/pnt/IOT/.agents/worker_remediate_final/report.md` and handoff in `/home/pnt/IOT/.agents/worker_remediate_final/handoff.md`
When done, notify parent via send_message.
