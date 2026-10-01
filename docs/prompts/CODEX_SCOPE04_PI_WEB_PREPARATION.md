# CODEX SCOPE-04 Pi Web Preparation — NOT START AUTHORIZED

**STATUS: `PREPARATION_ONLY — SCOPE04_BLOCKED_NOT_OPENED`**

Current blockers and decision packets: [SCOPE04_READINESS_REPORT.md](../reports/SCOPE04_READINESS_REPORT.md), [SCOPE04_ENTRY_OWNER_DECISION_PACKET.md](../reports/SCOPE04_ENTRY_OWNER_DECISION_PACKET.md), [SCOPE04_CAMERA_READONLY_AUTH_REQUEST.md](../reports/SCOPE04_CAMERA_READONLY_AUTH_REQUEST.md).

This is a repository-planning prompt, not authorization to implement SCOPE-04. Do not begin until the current SCOPE-04 readiness report records all required prerequisites as satisfied and the owner provides explicit progression approval.

## Preconditions to re-check

- SCOPE-02 owner acceptance is explicitly recorded, not merely PC-tested.
- SCOPE-03 has an accepted gate result appropriate to the authoritative project definition; current evidence includes an owner-attested N4 completion and a recorded SSH protocol deviation.
- Camera model, device permissions, supported modes and resource limits are inventoried.
- Pi identity/TLS policy is decided without linking Pi identity to PC Owner by assumption.
- Retention/legal hold is decided before any PC↔Pi status, telemetry, camera or PII exchange.
- Scope progression approval explicitly names SCOPE-04 and its time/boundary.

## Allowed preparation boundary

Prepare only local, read-only or mock components for:

- Pi-local authentication with a separate Pi identity domain;
- authenticated local camera stream adapter with typed unavailable/error states;
- offline map cache with provenance and visible stale labels;
- clearly labeled mock telemetry where unknown fields become `UNAVAILABLE`;
- 3D view using only verified fields;
- role, CSRF, rate-limit and upstream-down tests.

## Prohibitions

Do not add ARM/DISARM, actuator or flight-control routes; firmware flashing; public exposure; a command endpoint; fake approval; silent PC↔Pi identity federation; invented telemetry; or unapproved data transfer. Do not implement SCOPE-05/06 or later scopes.

## Required deliverables after approval

Create separate implementation, test and final reports with evidence classes. Keep mock fixtures distinct from live Pi evidence. Preserve rollback, typed errors and local-only boundaries. Stop if any requested feature would require an unresolved identity, TLS, retention or legal decision.
