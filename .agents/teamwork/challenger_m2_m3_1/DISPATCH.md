# Dispatch: Challenger 1 — Milestone 2 & 3 Stress & Empirical Verification

## Identity
- Role: Challenger 1 (M2 & M3 Empirical Verifier)
- TypeName: teamwork_preview_challenger
- Working Directory: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m2_m3_1
- Parent Conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81

## Authoritative Requirements & References
- Requirements: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md` (R3, R4)
- Project Spec: `c:\Users\pnt21\Desktop\IOT\PROJECT.md`
- M2 Worker Handoff: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m2\handoff.md`
- M3 Worker Handoff: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m3\handoff.md`

## Mission
Empirically stress-test the new server APIs and Pi gateway features:
1. Telemetry Ingestion: Stress test with high frequency envelopes, sequence out-of-order, timestamp replay attacks, malformed envelopes.
2. Latency Verification: Verify that telemetry posted via `POST /api/v1/device/telemetry` is immediately observable via `GET /api/v1/telemetry/latest` with < 2s propagation delay.
3. Exports: Validate RFC 7946 GeoJSON schema correctness with Shapely/GeoJSON validators; validate RFC 4180 CSV RFC conformity, special character escaping, commas, quotes, newlines in summaries.
4. Pi OTA Upload: Test with oversized file (>4MB), corrupted magic bytes, non-bin files, arming safety locks.

## Output
- Write findings and verdict (`APPROVE` or `REJECT`) to `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m2_m3_1\handoff.md` and send completion message.


## 2026-10-03T22:48:25Z
You are challenger_m2_m3_1, Challenger 1 (Stress & Empirical Verifier) for Milestone 2 & Milestone 3.
Your working directory is: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m2_m3_1
The authoritative requirements are in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md
The project specification is in: c:\Users\pnt21\Desktop\IOT\PROJECT.md
The worker handoff reports are in:
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m2\handoff.md
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m3\handoff.md
Please read your dispatch instructions at: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m2_m3_1\DISPATCH.md

Empirically stress-test telemetry latency (<2s), high-frequency envelope replay/skew, RFC 7946 GeoJSON and RFC 4180 CSV conformity, and Pi OTA upload bounds.
Write your findings and verdict (APPROVE or REJECT) to c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m2_m3_1\handoff.md, update progress.md, and send a message back to parent orchestrator (conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81).
