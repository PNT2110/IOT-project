# SCOPE-03 Next-Action Handoff

**STATUS: `CONSOLE_RECOVERY_UNVERIFIED — LIVE_CHANGE_BLOCKED`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Execution boundary:** PC-only review and document creation; no new SSH session, no Pi command and no network change.

## What is new in this turn

| Evidence class | Finding |
|---|---|
| `OWNER_REPORTED` | An external monitor is reported connected to the Pi. This does not prove keyboard, terminal, login or recovery. |
| `VERIFIED_IN_SOURCE` | Prior Mức B inventory and current live-change/recovery documents were read and compared; the prior SSH authorization is explicitly session-scoped. |
| `NOT_RUN` | No new SSH/console login, no `tty`/`id -un`/`uname -r` result from direct console, no Wi-Fi interruption and no network test. |
| `PROPOSED` | A non-executable Mức C approval draft was created with missing prerequisites and blank approval fields. |
| `BLOCKED` | Console login, keyboard, independent recovery, physical interface roles, AP capability, subnet conflict, identity/TLS and retention/legal hold remain unresolved. |

## Historical/current evidence distinction

| Artifact | Meaning |
|---|---|
| `SCOPE03_FINAL_REPORT.md`, `SCOPE03_TEST_REPORT.md` | Historical PC mock snapshot with `29 passed`; not modified. |
| `SCOPE03_HANDOFF_AFTER_AMENDMENT_FIX.md` | PC-only post-amendment handoff with `31 passed`; not a console or live-network result. |
| `SCOPE03_PI_READONLY_INVENTORY_RESULT.md` | One prior Mức B SSH read-only session; it observed Pi facts but left console/recovery unverified. |
| `SCOPE03_CONSOLE_RECOVERY_VERIFICATION.md` | This turn's console evidence matrix; local login remains unverified. |
| `SCOPE03_LIVE_CHANGE_APPROVAL_DRAFT.md` | Proposal-only draft; not approved and not executable. |

## Gate status

| Gate | Status | Meaning |
|---|---|---|
| SCOPE-02 amendment | `READY_FOR_OWNER_ACCEPTANCE` | PC evidence is ready; Owner acceptance is not recorded. |
| N0A | `PASS_PC_MOCK / PENDING_OWNER_ACCEPTANCE` | SCOPE-02 dependency is PC-tested, not owner-accepted. |
| N0B | `PASS_READ_ONLY_INVENTORY_FOR_PRIOR_SSH_SESSION` | Prior Mức B SSH inventory passed for that session only; it does not verify console recovery. |
| Console login | `UNVERIFIED` | Monitor is owner-reported; keyboard/TTY/direct login have no evidence. |
| Independent recovery | `UNVERIFIED` | Must be confirmed before any network change. |
| N1–N3 | `PASS_PC_MOCK / DESIGN_READY` | Mock/design evidence only; no new hardware inference. |
| N4 | `BLOCKED/NOT_RUN` | AP continuity while STA fails was not tested. |
| N5 | `PARTIAL/PENDING_OWNER` | Handoff prepared; Mức C approval and required owner decisions remain open. |

## Exact next actions requiring owner/operator input

1. At the Pi, confirm keyboard attachment, visible terminal/local TTY and direct non-root login; run only `tty`, `id -un`, `uname -r` locally and return redacted results.
2. Confirm an independent console/OOB recovery path; do not use the WLAN SSH path as proof.
3. Review and fill the blank fields in [SCOPE03_LIVE_CHANGE_APPROVAL_DRAFT.md](SCOPE03_LIVE_CHANGE_APPROVAL_DRAFT.md). Every proposed operation remains `PROPOSAL ONLY — NOT AUTHORIZED — DO NOT EXECUTE`.
4. Separately decide retention/legal hold, device identity/TLS and the PC↔Pi status/PII boundary.
5. Only after those decisions may the Owner issue a separate Mức C approval with snapshot, rollback, stop criteria and second-client verification.

```text
MONITOR_CONNECTED=OWNER_REPORTED
KEYBOARD_CONNECTED=UNVERIFIED
LOCAL_CONSOLE_LOGIN=UNVERIFIED
RECOVERY_DURING_NETWORK_FAILURE=NOT_TESTED
LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED
N4=BLOCKED/NOT_RUN
```

No SCOPE-04/05/06 work was opened. No password, PSK, TOTP, token, cookie, private key or PII was requested or recorded.
