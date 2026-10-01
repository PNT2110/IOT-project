# SCOPE-03 Handoff After SCOPE-02 Amendment Fix

**STATUS: `PARTIAL_PC_MOCK_PENDING_LIVE`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Basis:** [SCOPE02_AMENDMENT_CONSISTENCY_FINAL.md](SCOPE02_AMENDMENT_CONSISTENCY_FINAL.md)

## New handoff evidence

| Class | Finding |
|---|---|
| `VERIFIED_ON_PC` | The active role-review response no longer declares `OWNER_ONLY_REVIEW`; it returns `OWNER_OR_GRANTED_ADMIN_SCOPED` and effective action scopes. |
| `VERIFIED_ON_PC` | Account list/detail responses carry the same effective capability snapshot; the stale `OWNER_MUTATES_ADMIN_READS` value was removed from the active path. |
| `TESTED_ON_PC_MOCK` | Owner, ungranted Admin and granted Admin response/enforcement cases passed, including list filtering, self-review, Owner-elevation rejection, audit/history and negative scope paths. |
| `TESTED_ON_PC_MOCK` | Full SCOPE-01/02/03 regression passed: `31 passed, 1 warning`; frontend and dependency checks passed. |
| `BLOCKED` | Owner acceptance is not recorded. Retention/legal hold and any exact future live-network approval remain unresolved. |
| `NOT_RUN` | Pi inventory, SSH/console, real AP/STA continuity and Gate N4 were not run. |

## Required next decisions

1. Owner separately accepts or corrects the SCOPE-02 amendment consistency report.
2. Owner decides retention/legal hold before any PC↔Pi data exchange or public deployment.
3. Only after that, owner may issue a separate read-only Pi authorization for the exact device, operator, time, access method, command list and redacted output location using [SCOPE03_PI_READ_ONLY_ACCESS_REQUEST.md](SCOPE03_PI_READ_ONLY_ACCESS_REQUEST.md).
4. Before any live networking, independently verify console/out-of-band recovery and approve a separate change request with rollback details.

Read-only authorization would not authorize network changes. Historical IPs, usernames or credentials were not reused. No SCOPE-04/05/06 work was opened.
