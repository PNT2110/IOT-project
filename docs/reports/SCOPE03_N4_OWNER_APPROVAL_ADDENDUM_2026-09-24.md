# SCOPE-03 N4 Owner Approval Addendum — Conditional

**STATUS: `OWNER_LIVE_AUTHORIZATION=GRANTED — EXECUTION_RECONCILED`**  
**Captured:** 2026-09-24 (Asia/Ho_Chi_Minh)

## Approval received

The owner supplied a bounded approval for the SCOPE-03 N4 failure/recovery test only. It authorizes the stated read-only baseline first and, only if the verified topology matches, the exact STA disconnect/reconnect pair:

```text
FAILURE_INJECTION=disconnect only the verified upstream STA profile
RECOVERY=reactivate only the verified upstream STA profile
SCOPE04=NOT_AUTHORIZED
```

The approval explicitly prohibits AP profile changes, `ap0` down/delete, NetworkManager reset, firewall flush, manual route replacement, reboot, package installation, firmware/ESP32/GNSS work and later scopes.

## Why execution is still blocked

The approval itself requires these fields to be filled before it becomes executable, but they remain placeholders in the supplied record:

```text
TARGET_DEVICE_AND_PHYSICAL_LABEL=<OWNER FILL>
RESPONSIBLE_OPERATOR_AT_PI=<OWNER FILL>
APPROVED_TIME_WINDOW=<OWNER FILL>
OWNER_APPROVAL_TIMESTAMP=<OWNER FILL>
```

The approval also requires confirmation that the responsible operator is physically/local-console present for the whole test, that `LOCAL_CONSOLE_RECOVERY=VERIFIED_FOR_THIS_TEST`, and that `REAL_F450_CLIENT=VERIFIED`. Those conditions must be tied to the completed approval record before mutation.

No baseline command or mutation was executed while these required fields were incomplete. No password, PSK, OTP/TOTP, private key, saved secret or raw client identifier was recorded.

## Completion record received

```text
TARGET_DEVICE_AND_PHYSICAL_LABEL=Raspberry Pi 5 — hostname pitan — direct device at owner's desk
RESPONSIBLE_OPERATOR_AT_PI=Owner — physically present with local screen/terminal
APPROVED_TIME_WINDOW=2026-09-24 02:40–03:40 Asia/Ho_Chi_Minh
OWNER_APPROVAL_TIMESTAMP=2026-09-24 02:40 Asia/Ho_Chi_Minh
LOCAL_CONSOLE_RECOVERY=VERIFIED_FOR_THIS_TEST
REAL_F450_CLIENT=VERIFIED
OWNER_LIVE_AUTHORIZATION=GRANTED
```

The local PC clock was checked at `2026-09-24 03:09:46 +07`, inside the supplied approval window. The current prompt reports that the owner completed the sequence; no Pi command was run or independently observed by Codex from this workspace.

The prompt records this protocol deviation:

```text
N4_PROTOCOL_COMPLIANCE=DEVIATION_RECORDED
PROTOCOL_DEVIATION=N4 failure injection was initiated from SSH over wlan0 rather than from the approved local-console-only mutation path.
```

## Gate state

```text
OWNER_LIVE_AUTHORIZATION=GRANTED
LIVE_NETWORK_AUTHORIZATION=GRANTED_FOR_BOUNDED_TEST
N4=OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED
N4_PROTOCOL_COMPLIANCE=DEVIATION_RECORDED
N4_FAILURE_INJECTION=OWNER_ATTESTED_COMPLETION
N4_RECOVERY=OWNER_ATTESTED_COMPLETION
SCOPE04=NOT_OPENED
```

Before mutation, the owner must run the approved read-only baseline directly at the local Pi console and return redacted results. If any read-only fact differs from the expected topology, stop and request corrected approval; do not substitute another profile or command.
