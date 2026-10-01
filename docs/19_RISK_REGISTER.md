# SCOPE-00 — Risk register

| ID | Risk | Likelihood/impact | Mitigation / owner |
|---|---|---|---|
| R1 | Unverified GNSS/board causes UART/electrical conflict | M/H | Block S05; obtain model, schematic, level/power proof. |
| R2 | Firmware contains actuator path and unsafe assumptions | M/H | Read-only boundary; no server command path; safety review S07. |
| R3 | Map data unlicensed/outdated/misclassified | M/H | Provenance/license/effective date; legal review; separate internal/public. |
| R4 | AP+STA unsupported by USB chipset | M/H | Inventory chipset; lab test; fallback Ethernet/second adapter. |
| R5 | Email OTP unavailable offline | H/M | explicit `AUTH_UNAVAILABLE`; no silent bypass; recovery policy owner decision. |
| R6 | Dirty worktree leads to overwriting user work | H/H | no reset/restore; docs-only changes; owner resolves branch. |
| R7 | Telemetry stale/misleading | M/H | seq/timestamps/units/stale marker and `UNAVAILABLE`. |
| R8 | Public exposure before hardening | M/H | localhost-only S01; S08 gates; no claims of security. |
| R9 | PII/camera retention grows without purpose | M/M | minimization/retention/role review before storage. |
| R10 | Auth roles drift between PC/Pi | M/M | separate matrices, contract tests, explicit non-SSO. |

## Stop conditions

Any actuator command, unexplained privilege escalation, secret leak, legal-source ambiguity or hardware uncertainty that can affect safety stops the relevant scope and becomes `BLOCKED`.
