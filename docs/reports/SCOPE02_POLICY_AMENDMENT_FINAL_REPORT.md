# SCOPE-02 Policy Amendment — Final report

**STATUS: `PASS_REPORTED_PENDING_OWNER_ACCEPTANCE`**
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)

## Baseline

Repo `/home/pnt/IOT`, branch `main`, HEAD `16dc418076b1a53a9d2fc9af482e3a514f0791f7`; dirty/untracked SCOPE-00/01/02 worktree preserved. No DB runtime, scoped listener, Pi access or network mutation. Baseline before amendment: `19 passed`; frontend typecheck/build/pip check/diff check passed.

## Implemented change

- Added additive `capability_grants` model and Alembic revision `a71e8c4b2d90`.
- Added Owner-only grant/list/revoke routes and effective capability endpoint.
- Admin authorization now requires an active Owner grant, active MFA-ready session and exact object/action scope.
- Account grant: only `PENDING` `PC.GUEST` with verified email/TOTP may become `ACTIVE`.
- Role grant: only active `PC.GUEST` may become `ADMIN`; no reject, self-review, delegation or Owner grant.
- Revocation is DB-checked on every mutation and audited/history-recorded transactionally.
- UI displays effective capability and does not treat hidden buttons as authorization.
- Bootstrap Owner CLI path is unchanged and still requires exact phrase, password and current TOTP; no HTTP self-activation.

## Evidence

- Combined tests: `22 passed`, exit `0`, one upstream AnyIO deprecation warning.
- Python compile, frontend typecheck/build, pip check, diff check: exit `0`.
- Temporary migration upgrade/repeat/downgrade/restore: exit `0`; revision `a71e8c4b2d90`, `capability_grants` present.
- Existing dependency audit evidence remains valid because lockfiles did not change; no new dependency was added.
- SCOPE-03 preparation prompt/report created; no live Pi/network action.

## Amendment gate

| Gate | Result | Reason |
|---|---|---|
| A0 baseline/manifest/backup boundary | PASS | Baseline before code; no real DB existed; temp migration only. |
| A1 contract/matrix | PASS_REPORTED | Concrete Owner→Admin capability matrix documented; PC.GUEST≠Pi.USER. |
| A2 backend/security | PASS_REPORTED | Positive/negative grant/revoke/scope/stale/idempotency tests pass. |
| A3 regression/UI/docs | PASS_REPORTED | 22 tests, UI typecheck/build, contracts/docs/report complete; amendment browser role test not run. |
| A4 owner acceptance | BLOCKED_PENDING_OWNER | Owner must accept this amendment before it is treated as the new policy baseline or before live SCOPE-03. |

## Scope-03 handoff

Design-only artifacts:

- [CODEX_SCOPE03_PI_NETWORK_IMPLEMENTATION.md](../prompts/CODEX_SCOPE03_PI_NETWORK_IMPLEMENTATION.md)
- [SCOPE03_PREPARATION_REPORT.md](SCOPE03_PREPARATION_REPORT.md)

SCOPE-03 remains `DESIGN_MOCK_ONLY / BLOCKED_FOR_LIVE_PI`; no SSH, sudo, AP/STA change, firewall/DHCP/DNS/route change or reboot was performed.

## Owner decisions required

1. Accept the exact capability matrix and `PC.GUEST` mapping, or provide one corrected PC role mapping.
2. Accept additive migration revision `a71e8c4b2d90` and local-only amendment evidence.
3. Separately authorize live SCOPE-03 only after Pi facts, console/recovery path, subnet/SSID and rollback plan are supplied.
4. Chốt retention/legal hold before any real PC↔Pi data/PII exchange.

**Stop:** Do not start SCOPE-03 live work or SCOPE-04/05/06 until owner acceptance and the separate live-network gate are recorded.
