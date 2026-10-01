# SCOPE-05 Pi 5 Dedicated SSH-Key Validation

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## Validation command

The dedicated key-only validation was attempted exactly once with password and
keyboard-interactive authentication disabled:

```text
TARGET=pitan@192.168.1.118
KEY=/home/pnt/.ssh/id_ed25519_scope05_pi5
PI5_KEY_AUTH=FAILED
SSH_RESULT=PERMISSION_DENIED_PUBLICKEY
```

The Owner-reported bootstrap completion is retained as an external claim, but
the observed key authentication result was not successful. No password fallback
or second credential path was attempted.

## Client-key reconciliation

```text
LOCAL_PRIVATE_PUBLIC_MATCH=yes
LOCAL_PUBLIC_FINGERPRINT_MATCH=yes
EXPECTED_KEY_OFFERED=yes
SERVER_ACCEPTED_KEY=no
SSH_FAILURE_STAGE=SERVER_REJECTED_PUBLIC_KEY
PI5_KEY_RECONCILIATION=FAILED_SERVER_SIDE_KEY_INSTALLATION_REQUIRES_RECONCILIATION
```

The required Pi-local account and `authorized_keys` inspection remains
unavailable:

```text
PI5_LOCAL_USER=NOT_COLLECTED
AUTHORIZED_KEY_EXACT_MATCH=NOT_COLLECTED
AUTHORIZED_KEY_FINGERPRINT_MATCH=NOT_COLLECTED
SSHD_PUBKEYAUTH=NOT_COLLECTED
NEXT_GATE=PI5_LOCAL_AUTHORIZED_KEYS_RECONCILIATION_REQUIRES_PI_LOCAL_EXECUTION
```

Fast-track validation remains unsuccessful:

```text
FAST_TRACK_SSH_RETRY=FAILED
EXPECTED_KEY_OFFERED=yes
SERVER_ACCEPTED_KEY=no
NEXT_GATE=PI5_SSHD_POLICY_RECONCILIATION
FLASH_GATE=BLOCKED
```

## Pi and USB state

Because the remote command did not authenticate, the Pi identity command and
all Pi-side USB commands were not run:

```text
PI5_SHELL=UNAVAILABLE
USB_DIAG_HOST=NOT_PI5_VERIFIED
PI5_USB_EVIDENCE=NOT_COLLECTED
PI5_USB_ENUMERATION=NOT_COLLECTED
PI5_SERIAL_NODE=NOT_COLLECTED
PI5_CP2102_DRIVER_STATE=NOT_COLLECTED
PI5_KERNEL_USB_EVIDENCE=NOT_COLLECTED
PI5_PASSIVE_USB_EVENT=NOT_RUN
NEXT_GATE=PI5_KEY_INSTALLATION_RECONCILIATION
BUILD_GATE=BLOCKED
FLASH_GATE=BLOCKED
```

No PC-local USB evidence is promoted to current Pi evidence.
