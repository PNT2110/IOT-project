# SCOPE-04 Readiness Assessment

**STATUS: `SUPERSEDED_BY_PC_REPO_IMPLEMENTATION`**  
**Captured:** 2026-09-24 (Asia/Ho_Chi_Minh)  
**Scope:** Historical readiness snapshot. The direct Owner implementation
prompt has since completed the repository phase; see
`SCOPE04_FINAL_REPORT_CURRENT.md`. A bounded live Pi smoke has since executed;
the upstream-down acceptance gate remains unresolved.

## Entry-gate reconciliation against authoritative documents

The dependency graph in `docs/16_SCOPE_DEPENDENCIES.md` and the SCOPE-04 document require SCOPE-02 and SCOPE-03 to pass before SCOPE-04. The SCOPE-04 document additionally requires camera inventory and Pi identity policy. `docs/11_SECURITY_ARCHITECTURE.md` requires device identity/TLS and retention/deletion decisions for protected data and PC↔Pi/public boundaries; those are not silently promoted to local-only federation.

## Prerequisite matrix

| Prerequisite | Evidence | Status | Exact blocker / resolution path |
|---|---|---|---|
| SCOPE-02 PASS | Owner accepted the current capability/migration/bootstrap/response packet | `SATISFIED_BY_OWNER_ACCEPTANCE` | Acceptance is recorded; historical PC evidence remains unchanged. |
| SCOPE-03 PASS/accepted | Owner accepted technical result, evidence class, SSH deviation and no-rerun decision | `SATISFIED_BY_OWNER_ACCEPTANCE_WITH_DEVIATION` | N4 provenance remains `OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED`; not promoted to Codex live pass. |
| Camera inventory | Read-only Codex inventory identified `/dev/video0` UVC capture, `/dev/video1` metadata and successful metadata access | `PASS` | No stream/frame capture or persistence. |
| Pi identity policy | Owner accepted Pi-local USER/ADMIN boundary and no federation/sync | `SATISFIED_BY_OWNER_ACCEPTANCE` | Device identity/TLS remains deferred until actual PC↔Pi communication. |
| Retention/legal hold | Current SCOPE-02/SCOPE-03 records remain undecided | `OPEN_BLOCKER` | Owner/project decision required before integration or public deployment. |
| Explicit SCOPE-04 progression | Owner accepted `GRANT_AFTER_ALL_HARD_GATES_PASS` | `SATISFIED_CONDITIONALLY` | All listed hard gates now pass/are owner-accepted; implementation still requires its dedicated prompt/start. |

## Required decision classification

| Item | Classification | Current result |
|---|---|---|
| SCOPE-02 owner acceptance | `HARD_ENTRY_GATE` | Satisfied by explicit owner acceptance. |
| SCOPE-03 evidence level | `HARD_ENTRY_GATE` | Satisfied by explicit owner acceptance with deviation; evidence provenance unchanged. |
| Camera inventory | `HARD_ENTRY_GATE` | `CAMERA_INVENTORY=PASS`. |
| Pi-local identity policy | `HARD_ENTRY_GATE` | Satisfied by explicit local-only identity decision. |
| Device identity/TLS | `BLOCKS_ONLY_PC_PI_INTEGRATION` | Can remain deferred for strictly local-only preparation, subject to owner acceptance of the boundary. |
| Retention/legal hold | `BLOCKS_ONLY_PC_PI_INTEGRATION` and persistence/public deployment | Local-only preparation can keep recording/frame persistence off, but no protected-data persistence or integration is authorized before decisions. |
| Explicit SCOPE-04 progression | `HARD_ENTRY_GATE` | Satisfied conditionally by `GRANT_AFTER_ALL_HARD_GATES_PASS`; current gate audit is in `SCOPE04_FINAL_REPORT_CURRENT.md`. |

## SCOPE-03 closeout implication

The single-radio architecture is documented and the owner reports that the N4 sequence completed. The evidence class is not equivalent to a Codex-observed live test because the current repository contains no raw failure/recovery transcript. The protocol deviation—failure injection from SSH over `wlan0` instead of the approved local-console-only path—is recorded separately.

```text
SCOPE03_TECHNICAL_NETWORK=OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED
N4_PROTOCOL_COMPLIANCE=DEVIATION_RECORDED
SCOPE03_OVERALL=OWNER_ACCEPTED_WITH_DEVIATION
SCOPE04_READINESS_SNAPSHOT=SUPERSEDED_BY_IMPLEMENTATION_AND_LIVE_SMOKE
```

## What preparation may proceed

Repository-only preparation may define local-only auth, camera adapter interfaces, cache provenance/stale semantics, mock telemetry and negative tests. It must not add Pi runtime routes, public exposure, actuator/ARM/DISARM paths, firmware handling or silent PC↔Pi identity/data exchange.

## Smallest next action

This readiness snapshot is historical. Current implementation and live smoke
status are reconciled in `SCOPE04_FINAL_REPORT_CURRENT.md`.
