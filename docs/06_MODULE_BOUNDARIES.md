# SCOPE-00 — Module inventory và boundary

| ID/owner | In/out | Dependencies | Verified | Concern/test seam |
|---|---|---|---|---|
| PC-API / Codex | REST/realtime contracts, no actuator commands | Auth, DB, domain | `ASSUMPTION` | Contract tests; reject unknown command fields. |
| PC-AUTH / Codex | registration/login/MFA/session | Email, crypto lib, DB | `ASSUMPTION` | Fake email provider; rate-limit tests. |
| PC-GEO / Codex | canonical zones, provenance, version | GeoJSON validator, Shapely/PostGIS gate | `ASSUMPTION` | Fixtures with invalid winding/CRS/overlap. |
| PC-WF / Codex | simulated flight request state machine | PC-API, audit | `ASSUMPTION` | Idempotency and transition matrix. |
| PC-AUDIT / Codex | append-only event metadata | DB clock/actor | `ASSUMPTION` | Mutation must create event; secret redaction. |
| PI-NET / later | AP/STA/status probes | NetworkManager, OS | `USER_REPORTED` | Mock D-Bus; no shell injection. |
| PI-PORTAL / later | local config/recovery UI | PI-NET, Pi auth | `ASSUMPTION` | AP-only tests; CSRF/session. |
| PI-CAMERA / later | USB camera read-only stream | v4l2/encoder | `USER_REPORTED` | Mock device + resource budget. |
| PI-CACHE / later | map/status cache with stale metadata | PC API, disk | `ASSUMPTION` | Offline replay; age/error tests. |
| PI-TELEM / later | serial read-only framing | `/dev/tty*`, FC adapter | `ASSUMPTION` | Synthetic frames; no write path. |
| FC-AUDIT / SCOPE-05 | source inventory only initially | archive | `VERIFIED_FROM_SOURCE` | Static scan and passive capture plan. |
| GNSS-ADAPTER / SCOPE-05 | read-only NMEA/UBX after model proof | exact datasheet/wiring | `BLOCKED` | Parser fixtures; no config writes. |
| SHARED-CONTRACTS / Codex | versioned DTO/error/time/units | all domains | `ASSUMPTION` | JSON schema contract tests. |

## Ownership rule

The UI cannot grant a role, approve a request, or imply a legal permission. The backend/policy module is authoritative. Pi local ADMIN cannot mutate PC Owner data unless an explicit authenticated contract grants that operation; initial design grants none.

## Proposed repository tree (not created in SCOPE-00)

```text
docs/
server/          # SCOPE-01+ only
pi5/             # SCOPE-03+ only
contracts/       # SCOPE-01+ only
tests/            # each scope adds scoped tests
firmware/        # do not create/copy until SCOPE-05/07 approval
```
