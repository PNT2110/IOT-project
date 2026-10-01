# SCOPE-05 Pi 5 Local `authorized_keys` Reconciliation

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## Current evidence

The dedicated client key is valid and is offered, but the remote server rejects
it. There is no authenticated Pi shell through which the required local
reconciliation script can be executed.

```text
PI5_LOCAL_USER=NOT_COLLECTED
PI5_HOME=NOT_COLLECTED
AUTHORIZED_KEY_EXACT_MATCH=NOT_COLLECTED
AUTHORIZED_KEY_FINGERPRINT_MATCH=NOT_COLLECTED
SSH_DIR_OWNER_MODE=NOT_COLLECTED
AUTHORIZED_KEYS_OWNER_MODE=NOT_COLLECTED
SSHD_PUBKEYAUTH=NOT_COLLECTED
PI5_KEY_AUTH=FAILED
PI5_SHELL=UNAVAILABLE
```

## Observed client/server result

```text
LOCAL_PRIVATE_PUBLIC_MATCH=yes
LOCAL_PUBLIC_FINGERPRINT_MATCH=yes
EXPECTED_KEY_OFFERED=yes
SERVER_ACCEPTED_KEY=no
SSH_FAILURE_STAGE=SERVER_REJECTED_PUBLIC_KEY
```

This proves the remaining evidence domain is Pi-side account/home,
`authorized_keys`, ownership/permissions or sshd policy. It does not identify
which server-side condition is wrong without a Pi-local shell.

## USB consequence

```text
USB_DIAG_HOST=NOT_PI5_VERIFIED
PI5_USB_ENUMERATION=NOT_COLLECTED
PI5_SERIAL_NODE=NOT_COLLECTED
PI5_CP2102_DRIVER_STATE=NOT_COLLECTED
NEXT_GATE=PI5_LOCAL_AUTHORIZED_KEYS_RECONCILIATION_REQUIRES_PI_LOCAL_EXECUTION
FLASH_GATE=BLOCKED
```

No password fallback, sshd edit/restart, USB command, serial operation or
firmware operation was performed.
