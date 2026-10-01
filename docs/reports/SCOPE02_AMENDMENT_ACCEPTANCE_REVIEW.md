# SCOPE-02 Policy Amendment — Acceptance Review

**STATUS: `EVIDENCE_INCOMPLETE`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Review boundary:** PC source, reports, tests and temporary local SQLite only. No Pi, SSH, real network, public bind or credential handling.

## 1. Rebaseline

| Item | Observed |
|---|---|
| Repository | `/home/pnt/IOT` |
| Branch | `main` |
| HEAD | `16dc418076b1a53a9d2fc9af482e3a514f0791f7` |
| Baseline status | Dirty/untracked worktree preserved; no reset, clean, stash, checkout, commit or push. |
| Existing relevant reports | Amendment BASELINE, DECISIONS, IMPLEMENTATION, TEST and FINAL all present; SCOPE-03 FINAL and TEST present. |
| Existing dirty tracked files | `.gitignore`, `docs/05_SYSTEM_ARCHITECTURE.md`, `docs/09_API_CONTRACTS.md` |
| Existing untracked areas | `.env.example`, `README.md`, `contracts/`, `docs/10–20_*`, `docs/CODEX_*`, `docs/prompts/`, `docs/reports/`, `docs/scopes/`, `frontend/`, `pi5/`, `pytest.ini`, `server/`, `tests/` |

The status above is the pre-review baseline. The two required new reports and this review are new artifacts from this turn; pre-existing changes were not modified.

## 2. Decision summary

The amendment is substantially implemented and locally testable, but this review cannot mark it owner-accepted. Evidence is incomplete for several exact negative cases, and the role-review response still exposes the stale label `OWNER_ONLY_REVIEW` at `server/app/api.py:659-663`, although the amendment permits a specifically granted Admin to approve `GUEST → ADMIN`. This is recorded as a discrepancy; business policy was not changed in this turn.

`SCOPE02_AMENDMENT_ACCEPTANCE=NOT_RECORDED`  
`OWNER_ACCEPTANCE=NOT_RECORDED`  
`SCOPE03_LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED`

## 3. Requirement-to-evidence matrix

| Requirement | Code / file:line | Specific test evidence | Actual result | Gap / disposition |
|---|---|---|---|---|
| Admin may act only with an active Owner grant and MFA-ready active session | `server/app/api.py:166-188`; `server/app/services.py:92-94` | `tests/scope02/test_policy_amendment.py::test_admin_requires_owner_grant_and_grant_scope_is_enforced`; `::test_granted_admin_can_only_approve_guest_to_admin` | Current suite: PASS; 22 passed | Direct no-grant role-review endpoint assertion is not present; enforcement is code-backed and account mutation denial is tested. |
| Account approval is limited to pending `PC.GUEST` becoming active | `server/app/api.py:590-601`; `server/app/schemas.py:79-80,92-96` | `test_admin_requires_owner_grant_and_grant_scope_is_enforced` | PASS in current suite | The PC.GUEST mapping is an amendment decision, not a separately verified external identity fact. |
| Admin role approval is limited to `GUEST → ADMIN` and approval only | `server/app/api.py:665-687` | `test_granted_admin_can_only_approve_guest_to_admin` | PASS for approved path and rejected decision path | Stale response label `OWNER_ONLY_REVIEW` conflicts with delegated behavior; do not treat the label as current policy. Separate SCOPE-02 corrective change is needed. |
| No self-review / self-elevation | Account: `server/app/api.py:590-599`; role: `:665-672`; request creation: `:629-633` | `tests/scope02/test_account_and_roles.py::test_account_review_policy_status_version_and_session_revoke` covers account self-review; existing role tests cover Owner review path | Account self-review PASS; role self-review path is code-backed | No dedicated amendment test proves an Admin self-role request/review attempt is rejected. Evidence incomplete for this exact negative case. |
| No OWNER grant or OWNER elevation | Grant target restriction: `server/app/api.py:489-505`; role schema: `server/app/schemas.py:126-127`; defense in depth: `server/app/api.py:695-697` | Existing suite passes; no dedicated `requested_role=OWNER` request because schema excludes it | Code path prevents it | No direct API negative test for an explicit OWNER payload; add in a separate SCOPE-02 corrective prompt, not here. |
| Owner can grant concrete actions/scope; Admin/operator cannot grant | `server/app/api.py:489-513`; `server/app/schemas.py:92-111` | `test_admin_requires_owner_grant_and_grant_scope_is_enforced` | PASS: Admin/operator attempts return 403; Owner grant and idempotent replay succeed | No policy change made. |
| Owner revocation is immediate and removes effective capability | `server/app/api.py:532-558`; `server/app/services.py:92-94` | `test_admin_requires_owner_grant_and_grant_scope_is_enforced`; `test_capability_revoke_is_immediate_and_stale_version_is_safe` | PASS: post-revoke mutation 403; stale `If-Match` 409 | DB re-query behavior is verified by code and test; no live deployment evidence. |
| `If-Match`, idempotency and version safety | Grant revoke: `server/app/api.py:538-545`; account transition: `:602-609` | `test_capability_revoke_is_immediate_and_stale_version_is_safe`; account test stale/replay assertions | PASS in current suite | No new dependency or production DB was used. |
| Audit/history for mutation | Grant create/revoke: `server/app/api.py:509-511,554-556`; account/role: `:623-625,700-703` | Account audit/history assertions in `tests/scope02/test_account_and_roles.py:34-38`; amendment tests cover response paths | Account audit/history PASS; grant insertion is code-backed | No direct amendment assertion reads grant audit/history rows. Evidence incomplete for that narrower claim. |
| Session revocation is effective after suspend/reject | Session check: `server/app/api.py:88-106`; revoke-on-status: `:619-625` | `test_account_review_policy_status_version_and_session_revoke` | PASS: target session returns 401 and DB `revoked_at` is set | PC-local only. |
| Bootstrap Owner remains local-only with exact confirmation, password and TOTP | `server/cli.py:47-79` | Existing implementation report; no direct CLI subprocess test in the current SCOPE-01/02 suite | Source review PASS; automated direct test NOT PRESENT | Owner must accept the operational procedure; no secrets were requested or stored. |
| Amendment migration is reversible and restorable | `server/migrations/versions/a71e8c4b2d90_owner_admin_capability_grants.py:19-48`; model `server/app/models.py:198-213` | Temporary local SQLite cycle executed in this turn | PASS: `upgrade head` created table; downgrade removed it; restore returned revision `a71e8c4b2d90` and table present | No repository DB artifact was created. |
| Retention/legal hold before PC↔Pi exchange or public deploy | Prior decision: `docs/reports/SCOPE02_POLICY_AMENDMENT_DECISIONS.md` (unresolved decisions); final report owner actions | No implementation test applies | NOT DECIDED | Owner/project decision required before any integration or public deployment. |

## 4. Commands executed in this review

| Command | Exit | Result |
|---|---:|---|
| `.venv/bin/pytest -q tests/scope01 tests/scope02 -W default` | 0 | `22 passed, 1 warning`; warning is the upstream Starlette/AnyIO `BlockingPortal` deprecation. |
| `.venv/bin/python -m compileall -q server tests/scope01 tests/scope02` | 0 | PASS |
| `.venv/bin/pip check` | 0 | PASS — no broken requirements |
| `git diff --check` | 0 | PASS |
| Temporary local SQLite: Alembic `upgrade head → inspect → downgrade 9c4f2d7e6a11 → inspect → upgrade head → inspect` | 0 | PASS — amendment table lifecycle and final revision verified |

No Pi/SSH/network command was executed. No live SCOPE-03 gate was run.

## 5. Owner decisions still required

1. Accept or correct the exact Owner → Admin capability matrix and the `PC.GUEST` mapping.
2. Accept the additive migration `a71e8c4b2d90` and the local-only bootstrap procedure.
3. Decide how the stale `OWNER_ONLY_REVIEW` response/documentation label is to be corrected in a separate SCOPE-02 change.
4. Decide retention/legal hold before any PC↔Pi exchange, integration or public deployment.
5. If live SCOPE-03 is later desired, issue a separate authorization naming the exact Pi, read-only inventory scope, independent recovery path and network-change boundary.

This report does not record owner acceptance and does not authorize SCOPE-03 live work or SCOPE-04/05/06.
