# SCOPE-02 Amendment Closeout Verification

**STATUS: `READY_FOR_OWNER_ACCEPTANCE`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Execution boundary:** PC/local-only source, test client, documentation and temporary SQLite. No Pi, SSH, live network, external provider or public bind.

## Baseline and manifest

| Item | Verified value |
|---|---|
| Repository | `/home/pnt/IOT` |
| Branch / HEAD | `main` / `16dc418076b1a53a9d2fc9af482e3a514f0791f7` |
| Worktree | Existing dirty/untracked SCOPE-00/01/02/03 work preserved; no reset, clean, stash, checkout, commit, push or deletion. |
| Source changes in this turn | `NONE`; current implementation was already consistent, so no code-only diff was created. |
| New files in this turn | This closeout, [SCOPE03_READ_ONLY_INVENTORY_APPROVAL_PACKET.md](SCOPE03_READ_ONLY_INVENTORY_APPROVAL_PACKET.md), and [SCOPE03_NEXT_GATE_HANDOFF.md](SCOPE03_NEXT_GATE_HANDOFF.md). |
| Historical figures | Earlier 22/29-pass reports were not reused as current execution evidence. The commands below were run in this turn. |

## Policy and enforcement matrix

| Policy expected | Actual source/contract | Test evidence from this turn | State |
|---|---|---|---|
| Owner grants/revokes only concrete capabilities for another active PC Admin | `server/app/api.py:489-558`; `server/app/schemas.py:92-123`; `server/app/services.py:92-94` | `test_admin_requires_owner_grant_and_grant_scope_is_enforced`; `test_capability_revoke_is_immediate_and_stale_version_is_safe` | `VERIFIED_IN_SOURCE` + `TESTED_ON_PC` |
| Admin without grant fails closed | `server/app/api.py:173-188` | `test_review_responses_expose_effective_scope_and_not_owner_only`; full regression | `TESTED_ON_PC` — role-review 403 and scopes `NONE` |
| Account capability is only pending PC GUEST → ACTIVE | `server/app/api.py:611-648` | `test_admin_requires_owner_grant_and_grant_scope_is_enforced` | `VERIFIED_IN_SOURCE` + `TESTED_ON_PC` |
| Role capability is only active PC GUEST → ADMIN approval | `server/app/api.py:680-717` | `test_granted_admin_can_only_approve_guest_to_admin` | `VERIFIED_IN_SOURCE` + `TESTED_ON_PC` |
| No self-review, Admin→Owner, grant/redelegation | `server/app/api.py:650-672,704-717`; `server/app/schemas.py:126-149` | `test_role_self_review_and_owner_elevation_are_rejected_without_side_effect`; existing grant negative tests | `TESTED_ON_PC` — 403/422 and no mutation |
| Effective representation is consistent | `server/app/api.py:191-210,598-609,680-687`; `frontend/src/api.ts:101-134`; `frontend/src/App.tsx:239-264` | `test_review_responses_expose_effective_scope_and_not_owner_only` | `TESTED_ON_PC` — `OWNER_OR_GRANTED_ADMIN_SCOPED`, action/scope metadata, list filtering |
| Historical `OWNER_ONLY_REVIEW` is not active API/UI policy | Active source/API/UI search; historical reports retained | `assert "OWNER_ONLY_REVIEW" not in str(role_data)` plus source inspection | `VERIFIED_IN_SOURCE` + `TESTED_ON_PC`; historical occurrences are explicitly historical/report-only |
| Session revoke, audit/history, idempotency and version safety | `server/app/api.py:88-106,619-648,704-717` | SCOPE-02 regression and amendment tests | `TESTED_ON_PC` |
| Bootstrap Owner remains local-only | `server/cli.py:47-79` | Source inspection; no live CLI bootstrap invoked | `VERIFIED_IN_SOURCE`; execution `NOT_RUN` by design |
| Migration round-trip | `server/migrations/versions/a71e8c4b2d90_owner_admin_capability_grants.py:19-48` | Temporary SQLite upgrade/downgrade/restore | `TESTED_ON_PC` |
| Retention/legal hold | Prior decision documents leave duration undecided | No code test applies | `OWNER_DECISION_PENDING` |

No PC `USER` role was invented; current PC roles remain `GUEST/OPERATOR/ADMIN/OWNER`. Pi `USER/ADMIN` remains a separate identity domain.

## DTO and UI closeout

The active response contract retains compatibility booleans and adds:

```text
policy = OWNER_OR_GRANTED_ADMIN_SCOPED
account_approve = {allowed, scope}
admin_role_approve = {allowed, scope}
```

Owner receives broad current PC workflow scopes subject to self-review rules. A granted Admin receives only `PENDING_PC_GUEST_TO_ACTIVE` and/or `ACTIVE_PC_GUEST_TO_ADMIN_APPROVE_ONLY`. The UI displays these effective scopes and uses them only as affordances; backend authorization remains authoritative.

## Commands actually run

| Command | Exit | Result |
|---|---:|---|
| `.venv/bin/pytest -q tests/scope01 tests/scope02 tests/scope03 -W default` | 0 | `31 passed, 1 warning` |
| `.venv/bin/python -m compileall -q server pi5 tests/scope01 tests/scope02 tests/scope03` | 0 | PASS |
| `npm --prefix frontend run typecheck` | 0 | PASS |
| `npm --prefix frontend run build` | 0 | PASS; Vite 7.3.6 |
| `.venv/bin/pip check` | 0 | PASS |
| `.venv/bin/pip-audit -r server/requirements.lock --format columns` | 0 | No known vulnerabilities |
| `npm --prefix frontend audit --omit=dev --audit-level=high` | 0 | 0 vulnerabilities |
| `git diff --check` | 0 | PASS |
| Temporary SQLite: `upgrade head → inspect → downgrade 9c4f2d7e6a11 → inspect → upgrade head → inspect` | 0 | Head/restored `a71e8c4b2d90`; `capability_grants` true, downgraded false |

The only warning was the upstream Starlette/AnyIO `BlockingPortal` deprecation at `.venv/lib/python3.14/site-packages/starlette/testclient.py:53`.

## Acceptance boundary

`OWNER_ACCEPTED=NOT_RECORDED`  
`SCOPE02_AMENDMENT_ACCEPTANCE=READY_FOR_OWNER_ACCEPTANCE`

This report is evidence for owner review, not owner acceptance. The owner must separately accept or correct the capability matrix, PC `GUEST` mapping, additive migration/local bootstrap procedure, and retention/legal-hold decision. No SCOPE-03 live authorization is implied.
