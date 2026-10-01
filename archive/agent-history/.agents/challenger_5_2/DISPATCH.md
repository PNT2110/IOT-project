# DISPATCH — challenger_5_2
Timestamp: 2026-09-14T04:00:00+07:00

## Identity & Role
- Agent Name: challenger_5_2
- Archetype: teamwork_preview_challenger
- Working Directory: /home/pnt/IOT/.agents/challenger_5_2
- Parent Conversation ID: ec132afd-20fb-4e3f-8ced-f823b42ac295

## Context & Input Files
- User Request: /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (specifically request at 2026-09-13T20:45:54Z)
- Specification: /home/pnt/IOT/prompt-du-an-drone-v2.md
- Project Scope: /home/pnt/IOT/PROJECT.md
- Test Status: /home/pnt/IOT/TEST_REPORT.md

## Key Constraints
- Bare-metal / systemd on Pi5 (DO NOT use Docker).
- Fail-safe ARM locking: lock ARM if MOD approval is absent/invalid, outside coordinates/time window (>1km), or invalid data. NEVER set ENABLE_REAL_FLIGHT_COMMANDS=true.
- Security hardening (R6):
  * Absolute rule: DO NOT change password of user `pi5` (must remain `123456`).
  * Absolute rule: DO NOT disable Password Authentication on Pi5.
  * Pi5 IP is `192.168.1.118`.

## Adversarial Verification Objectives
1. Adversarial Challenge on Geofence & Serial Robustness:
   - Challenge Geofence engine with points right on boundary, collinear vertices, self-intersecting polygons, invalid lat/lon values.
   - Challenge anti-replay protection on MOD flight requests (duplicate nonce, stale timestamp >300s).
   - Challenge firmware integrity verification: attempt uploading truncated/corrupted firmware or mismatched sha256 checksums.
2. Verification Execution:
   - Run tests directly and inspect responses.
3. Output Requirements:
   - Write comprehensive report in `report.md` and `handoff.md` in `/home/pnt/IOT/.agents/challenger_5_2/`.
   - Provide an explicit verdict: `APPROVE` or `REJECT`.
   - Send completion message to parent.
