# SCOPE-00 — Master roadmap

| Scope | Goal | Gate/status |
|---|---|---|
| 00 | Research & Architecture | This document set; pending owner approval. |
| 01 | PC Server Foundation | Local only: auth/RBAC, simulated map, base API. Must pass SCOPE-00 approval. |
| 02 | PC Workflow/API | Simulated requests, audit, Pi-facing API. Needs 01. |
| 03 | Pi Network | AP + USB STA + recovery; no drone intervention. Needs hardware inventory. |
| 04 | Pi Web | Auth, webcam, cache, mock telemetry. Needs 02/03. |
| 05 | ESP32 Read-only Audit/GNSS | Passive/read-only desk testing only. Needs model/wiring/safety plan. |
| 06 | Integration | End-to-end simulated PC↔Pi↔ESP telemetry read-only. Needs 02,04,05. |
| 07 | Firmware & Safety Review | Separate safety design/review; no implied flight permission. Needs evidence and approval. |
| 08 | Deployment & Hardening | Legal/network/TLS/DR/security test before any public exposure. Needs all gates. |

SCOPE-01 is the first code scope but is locked until the owner approves SCOPE-00 and resolves its preconditions in [CODEX_SCOPE01_PROMPT.md](CODEX_SCOPE01_PROMPT.md).
