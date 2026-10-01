# SCOPE-02 Amendment Consistency — Baseline and Manifest

**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Baseline status:** PC/local-only; no Pi, SSH, live network, public bind or external integration.

## Repository baseline

| Item | Value |
|---|---|
| Root | `/home/pnt/IOT` |
| Branch | `main` |
| HEAD | `16dc418076b1a53a9d2fc9af482e3a514f0791f7` |
| Python / Node / npm | Python 3.14.7 / Node v22.22.1 / npm 9.2.0 |
| Test tool | `.venv/bin/pytest` 9.1.1 |
| Worktree | Dirty/untracked existing SCOPE-00/01/02/03 artifacts preserved; no reset, clean, stash, checkout, commit, push or deletion. |
| Historical evidence | Prior report stated 22 SCOPE-01/02 tests and migration cycle passed; those numbers are historical until rerun in this corrective turn. |

## Source-of-truth findings before modification

| Finding | Evidence | Consequence |
|---|---|---|
| Role-review enforcement already permits a granted Admin | `server/app/api.py:182-188,665-687`; `server/app/services.py:92-94` | Backend authorization reflects the amendment. |
| Role-review response is stale | `server/app/api.py:659-663` returns `policy: OWNER_ONLY_REVIEW` | A caller can receive a policy description that contradicts effective authorization. |
| Account-review list response is stale | `server/app/api.py:560-577` returns `role_policy: OWNER_MUTATES_ADMIN_READS` | It omits the granted Admin account-approval mutation scope. |
| Current docs contain pre-amendment wording | `docs/09_API_CONTRACTS.md:58-60`, `contracts/v1/README.md:23,29`, `docs/10_AUTHENTICATION_RBAC.md:37-39` | Contract/RBAC readers can infer Owner-only behavior after the amendment. |
| UI approval buttons use backend capability flags | `frontend/src/App.tsx:239-244,264`; `frontend/src/api.ts:101-124` | No role-only approval button was found; response scope detail is not typed/displayed. |
| Historical strings remain in old reports/tests | `docs/reports/**`, `tests/scope02/test_account_and_roles.py:41` | Historical reports are not overwritten; test names may be clarified only if behavior/representation tests are added. |

## Policy boundary retained

- Owner grants/revokes only concrete capabilities to a specific active PC Admin.
- `ACCOUNT_APPROVE` is limited to pending PC `GUEST → ACTIVE`.
- `ADMIN_ROLE_APPROVE` is limited to active PC `GUEST → ADMIN`, approval only.
- No Admin grant/redelegation, self-review, Owner elevation or Pi identity federation.
- Existing local-only Owner bootstrap (exact confirmation, password and current TOTP) remains unchanged.
- No `USER` role is invented; the current PC enum remains `GUEST/OPERATOR/ADMIN/OWNER`.

## Change manifest

### `READ_ONLY`

- Existing SCOPE-02 amendment reports and SCOPE-03 handoff/access reports.
- `server/app/api.py`, `server/app/services.py`, models, schemas and migration.
- `frontend/src/App.tsx`, `frontend/src/api.ts`.
- Current RBAC/API contract docs and SCOPE-02 tests.

### `MODIFY`

- `server/app/api.py`: replace stale policy labels, add a scope-aware effective-capability representation to review responses, and filter the delegated Admin role-review list to eligible targets without changing authorization policy.
- `frontend/src/api.ts`, `frontend/src/App.tsx`: type and display effective scope; retain backend as authority and avoid role-only approval decisions.
- `docs/09_API_CONTRACTS.md`, `contracts/v1/README.md`, `docs/10_AUTHENTICATION_RBAC.md`: update current contract/RBAC wording; preserve historical reports.
- `tests/scope02/test_policy_amendment.py`, `tests/scope02/test_account_and_roles.py`: add representation, no-grant, scope, self-review and Owner-only negative coverage.

### `CREATE`

- `docs/reports/SCOPE02_AMENDMENT_CONSISTENCY_IMPLEMENTATION.md`
- `docs/reports/SCOPE02_AMENDMENT_CONSISTENCY_TEST.md`
- `docs/reports/SCOPE02_AMENDMENT_CONSISTENCY_FINAL.md`
- `docs/reports/SCOPE03_HANDOFF_AFTER_AMENDMENT_FIX.md`

No persistence schema change is planned for this correction; migration downgrade/restore will be checked only on a temporary database if the implementation remains schema-free.
