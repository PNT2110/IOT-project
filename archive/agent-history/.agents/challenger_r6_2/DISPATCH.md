# DISPATCH — Challenger R6-2 (Adversarial Testing: Serial USB, Firmware, and MOD Server)

## Working Directory
/home/pnt/IOT/.agents/challenger_r6_2

## Mandatory References
1. Original request: `/home/pnt/IOT/.agents/ORIGINAL_REQUEST.md` (section `## 2026-09-14T05:07:21Z`)
2. Worker handoff report: `/home/pnt/IOT/.agents/worker_r6_1/handoff.md`
3. Project Architecture: `/home/pnt/IOT/PROJECT.md`

## Task
Adversarially challenge and stress-test:
1. **Serial USB (R2)**:
   - Challenge port disconnect and reconnect simulation: simulate device unplugging and replugging under a new simulated port name; verify that coordinator releases device and auto-reacquires without crashing.
   - Challenge corrupted JSONL: feed garbage, malformed json, empty lines, NaN floats; verify worker survives without throwing uncaught exceptions.
2. **Static Firmware Flashing & Fail-Safe ARM (R3)**:
   - Challenge custom firmware upload: call `POST /api/v1/firmware/upload`; assert that it strictly returns HTTP 403 Forbidden.
   - Challenge ARM lockout when official firmware is missing: simulate missing `official.bin` (and repo fallback); assert that `POST /api/v1/commands/arm` returns HTTP 423 Locked and ARM safety monitor revokes ARM.
3. **MOD Server Apps Script (R5)**:
   - Challenge `backend/mod_server.gs`: verify syntax, 1km geodesic circle calculation (64 vertices, distance ~1000m from center), anti-replay timestamp skew check (>300s rejected), duplicate nonce rejected.
   - Challenge `backend/app/main.py` client: verify `httpx.AsyncClient` has `follow_redirects=True` and reads `MOD_WEBAPP_URL`.

Write your stress tests / verification scripts and document results in `/home/pnt/IOT/.agents/challenger_r6_2/handoff.md` with a clear verdict: `APPROVE` or `REQUEST_CHANGES`. Send a completion message to parent when done.
