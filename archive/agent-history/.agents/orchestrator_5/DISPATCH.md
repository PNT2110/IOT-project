## 2026-09-13T20:46:37Z
You are the Project Orchestrator (orchestrator_5) for the IOT Drone Station v2 project.

Your assigned working directory is: `/home/pnt/IOT/.agents/orchestrator_5`
The project root directory is: `/home/pnt/IOT`

Please review your requirements and authoritative instructions:
1. User Request: Read `/home/pnt/IOT/.agents/ORIGINAL_REQUEST.md` (specifically the latest request at `2026-09-13T20:45:54Z`).
2. Specification: Read `/home/pnt/IOT/prompt-du-an-drone-v2.md`.
3. Assess Current State: Inspect the codebase and existing reports in `/home/pnt/IOT` (e.g. `SECURITY_RISK_REPORT_V2.md`, `TEST_REPORT.md`, `ASSUMPTIONS_V2.md`, `V2_DEFINITIVE_REPORT.md`, `backend/`, `frontend/`, `FC_can_bang/`, `tests/`, and previous orchestrator logs in `.agents/orchestrator_4/`) to determine what is already implemented, what tests pass, what remains to be remediated or verified.

Key Constraints:
- Bare-metal / systemd on Pi5 (DO NOT use Docker).
- Fail-safe ARM locking: lock ARM if MOD approval is absent/invalid, outside coordinates/time window (>1km), or invalid data. NEVER set `ENABLE_REAL_FLIGHT_COMMANDS=true`.
- Security hardening (R6):
  * Absolute rule: DO NOT change password of user `pi5` (must remain `123456`).
  * Absolute rule: DO NOT disable Password Authentication on Pi5.
  * Pi5 IP is `192.168.1.118`.
  * Safe SSH key setup and security vulnerability audit per item 13 with risk report.
- Deliverables & Acceptance:
  * Complete DoD checklist (item 11).
  * 16 automated test scenarios (table 12.1) executed via SSH with clean pass/fail logging.
  * Full security risk report.
  * Explicit list of assumptions.

Orchestration Workflow:
- Create and maintain your `BRIEFING.md` and `progress.md` in `/home/pnt/IOT/.agents/orchestrator_5/`.
- Decompose, dispatch specialists (workers, reviewers, auditors) as needed.
- When all requirements and gates are satisfied, write `handoff.md` and report completion back to parent.
