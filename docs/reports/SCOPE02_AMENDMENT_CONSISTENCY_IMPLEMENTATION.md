# SCOPE-02 Amendment Consistency — Implementation Report

**STATUS: `IMPLEMENTED_PC_LOCAL_ONLY_PENDING_OWNER_ACCEPTANCE`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Baseline:** [SCOPE02_AMENDMENT_CONSISTENCY_BASELINE.md](SCOPE02_AMENDMENT_CONSISTENCY_BASELINE.md)

## Change made

The stale active-policy representation was corrected without changing the delegated policy or adding a new role:

- `server/app/api.py:191-210` adds one effective-capability snapshot used by account and role-review responses.
- `server/app/api.py:598-609` replaces `OWNER_MUTATES_ADMIN_READS` with `OWNER_OR_GRANTED_ADMIN_SCOPED` and includes per-action effective scope in account list/detail responses.
- `server/app/api.py:680-687` replaces `OWNER_ONLY_REVIEW`, returns the same effective-capability metadata, and filters a delegated Admin's role-review list to active `GUEST → ADMIN` requests.
- Existing compatibility flags `can_approve_accounts` and `can_approve_admin_role` remain present. The backend remains authoritative for every mutation.
- `frontend/src/api.ts:101-135` types the policy and per-action scope metadata; `frontend/src/App.tsx:264` displays effective scope and uses the effective `allowed` flags for buttons. No approval decision is derived from `role === ADMIN`.
- `docs/09_API_CONTRACTS.md`, `contracts/v1/README.md` and `docs/10_AUTHENTICATION_RBAC.md` now distinguish the pre-amendment baseline from the current Owner-granted Admin capability.
- `tests/scope02/test_policy_amendment.py` adds representation, no-grant, target filtering, self-review, Owner elevation, audit/history and list/detail assertions. The stale test name in `test_account_and_roles.py` was clarified.

## Current response contract

Review responses retain the v1 envelope and compatibility booleans and now expose:

```json
{
  "policy": "OWNER_OR_GRANTED_ADMIN_SCOPED",
  "can_approve_accounts": false,
  "can_approve_admin_role": false,
  "account_approve": {"allowed": false, "scope": "NONE"},
  "admin_role_approve": {"allowed": false, "scope": "NONE"}
}
```

Effective scope values are descriptive metadata, not an authorization bypass:

- Owner: `ALL_ACCOUNT_STATUS_TRANSITIONS_EXCEPT_SELF` and `ALL_ROLE_ELEVATIONS_EXCEPT_SELF`.
- Granted Admin: `PENDING_PC_GUEST_TO_ACTIVE` and `ACTIVE_PC_GUEST_TO_ADMIN_APPROVE_ONLY`.
- No active grant or inactive/MFA-incomplete caller: `NONE`.

## Policy invariants preserved

- Owner alone creates/revokes grants; a grant targets another active PC `ADMIN` and is scoped to `PC_GUEST`.
- Admin account approval requires `ACCOUNT_APPROVE` and is limited to pending PC `GUEST → ACTIVE`.
- Admin role approval requires `ADMIN_ROLE_APPROVE` and is limited to approval of active PC `GUEST → ADMIN`.
- Admin cannot grant/redelegate, self-review, grant or obtain `OWNER`, or mutate out-of-scope targets.
- The current PC enum remains `GUEST/OPERATOR/ADMIN/OWNER`; no ambiguous `USER` role was added.
- Existing local-only Owner bootstrap CLI remains unchanged.
- No persistence schema or migration was modified by this corrective turn.

## Historical strings

`OWNER_ONLY_REVIEW` remains only where explicitly identified as historical in existing amendment documentation and the new negative assertion. Old reports were not overwritten. No active API response, current contract, current RBAC section or UI label uses it as the current policy.

## Remaining acceptance boundary

This is a local implementation result, not Owner acceptance. Retention/legal hold still has no owner-selected duration and must be decided before any PC↔Pi exchange or public deployment. SCOPE-03 remains mock-only; no live Pi or network work was authorized or performed.
