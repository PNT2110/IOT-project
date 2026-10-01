# SCOPE-00 — Acceptance criteria và traceability

## SCOPE-00 acceptance

- All required Markdown files exist and are non-empty.
- Every architecture decision has context, alternative, trade-off, rollback and evidence status.
- Mermaid diagrams cover context/module/network/identity/dataflow/safety/operations at least at design level.
- Firmware findings are limited to archive evidence; GNSS/model gaps are `BLOCKED`.
- No source/firmware/hardware/network mutation occurred.
- Every scope has prerequisites, tests, evidence, rollback, DoD and approval gate.

## Traceability sample

| Requirement | Module/API | Scope | Test/acceptance |
|---|---|---|---|
| REQ-PUB-01 | PC-GEO, `GET /public/zones` | 01/02 | Guest cannot read internal fixture; 403/filtered response. |
| REQ-AUTH-02 | PC-AUTH/PiAuth | 01/04 | fake email unavailable returns `AUTH_UNAVAILABLE`; no session elevation. |
| REQ-PI-NET-02 | PI-NET `/health/network` | 03 | three booleans independently simulated and displayed. |
| REQ-GNSS-01 | GNSS adapter contract | 05/06 | no-fix/null/stale fixtures; no fabricated coordinate. |
| REQ-WF-02 | PC-WF/Pi sync | 02/06 | serialized approval contains `simulated=true` and no actuator field. |
| NFR-SEC-01 | Auth/log/audit | 01–08 | secret scanner + redacted fixture review. |
| NFR-OFF-01 | PI-NET/PI-CACHE/PI-CAMERA | 03/04/06 | upstream down while AP/local services remain reachable in lab. |

Quantitative thresholds such as latency, FPS, stale-after and retention duration remain open until a benchmark/protection owner approves them; no unrun measurement is claimed.
