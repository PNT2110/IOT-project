# SCOPE-02 Policy Amendment — Baseline report

**Status:** `A0_COMPLETE_BEFORE_CODE`
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)
**Purpose:** chốt thay đổi policy capability grant cho Admin; không triển khai SCOPE-03 live network.

## Repository/runtime rebaseline

| Item | Evidence |
|---|---|
| Root / branch / HEAD | `/home/pnt/IOT` / `main` / `16dc418076b1a53a9d2fc9af482e3a514f0791f7` |
| Worktree | Dirty và nhiều file untracked thuộc SCOPE-00/SCOPE-01/SCOPE-02; giữ nguyên, không reset/clean/stash/checkout/commit/push. |
| Runtime | Python `3.14.7`; Node `v22.22.1`; npm `9.2.0`; project `.venv` và lockfiles hiện hữu. |
| DB/ports | Không có `*.db`/`*.sqlite*` trong repo; không có listener `8765`, `5173`, `8000` tại baseline. Không có DB thật để backup; migration chỉ chạy DB tạm. |
| Baseline tests | `.venv/bin/pytest -q tests/scope01 tests/scope02 -W default` → exit `0`, `19 passed`, `1` upstream warning. Frontend typecheck/build, pip check, diff check đều exit `0`. |
| External state | Không SSH/Pi/firmware/hardware/network/public service; `FC_can_bang.zip` read-only. |

## Current source vs owner policy

Current source has `User` roles `GUEST`, `OPERATOR`, `ADMIN`, `OWNER`; statuses `PENDING`, `ACTIVE`, `REJECTED`, `SUSPENDED`. SCOPE-02 currently makes `OWNER` the only account/role reviewer and allows `ADMIN` read-only review. The new owner decision supersedes that behavior only for the amendment:

- `PC.GUEST` is the current source-level mapping for an ordinary authenticated PC user after activation; it is not `Pi.USER` and no identity federation is introduced.
- `OWNER` may grant a capability to one `ACTIVE` PC `ADMIN` principal.
- A granted Admin may only approve `PENDING → ACTIVE` ordinary PC users (`role == GUEST`) and approve a role elevation to `ADMIN` for an active ordinary PC user, within the explicit grant action/scope.
- No Admin grant may grant/revoke grants, approve another Admin/Owner, change Owner status, self-review, delegate, or grant `OWNER`.
- Revocation is immediate because each mutation re-queries the DB; no cached authorization is used. No expiry is invented because the owner decision does not specify an expiry duration; `revoked_at` is explicit and revocation is immediate.
- Pending/suspended/rejected actors cannot review regardless of stored role. Pi `USER/ADMIN` remains a separate identity domain.

## Change manifest

| Classification | Paths | Planned action |
|---|---|---|
| `MODIFY` | `server/app/models.py`, `schemas.py`, `services.py`, `api.py` | Add capability grant entity/DTO/policy checks and update account/role review authorization. |
| `CREATE` | One additive Alembic migration; amendment tests; four amendment reports; SCOPE-03 preparation prompt/report | Additive schema, negative/positive tests, design-only handoff. |
| `MODIFY` | `contracts/v1/README.md`, `docs/09_API_CONTRACTS.md`, `docs/10_AUTHENTICATION_RBAC.md`, SCOPE-02 decisions addendum, frontend role capability display | Document owner-granted capability and backend-authoritative UI. |
| `READ_ONLY` | `FC_can_bang.zip`, firmware, Pi/network state, historical SCOPE-01/02 reports, SCOPE-03/04 scope docs | No mutation. |
| `FORBIDDEN` | SSH/sudo/network changes on Pi, public bind, real providers, PII sync, firmware/ESP32/GNSS/control paths | Not authorized by this prompt. |

## Open point resolved from source

The “USER” wording is mapped to active PC `GUEST`, the only source role that represents the ordinary non-reviewing PC account and is already accepted by the current role-elevation implementation. It is explicitly not mapped to Pi `USER`; no clarification blocker remains for this amendment. If the owner intends a distinct PC `USER` role, that is a later breaking domain decision, not silently introduced here.

## A0 result

`A0_COMPLETE_BEFORE_CODE`: baseline evidence and manifest are recorded before amendment code changes. Proceed only with additive capability-grant policy work and local/mock SCOPE-03 preparation.
