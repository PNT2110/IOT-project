# SCOPE-05 One-Time Pi 5 SSH-Key Bootstrap

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## Dedicated local key

```text
PI5_AUTOMATION_KEY_FINGERPRINT=SHA256:VrUiXWY9kkxBKt+BwjXv6NMBtsUxOl8kxBXR+rv46i4
PI5_KEYPAIR_PREPARED=yes
PI5_PUBLIC_KEY_COMMENT=scope05-pi5-automation
PI5_PRIVATE_KEY_PATH=/home/pnt/.ssh/id_ed25519_scope05_pi5
PI5_PUBLIC_KEY_PATH=/home/pnt/.ssh/id_ed25519_scope05_pi5.pub
PI5_PRIVATE_KEY_PERMISSIONS=600
PI5_PUBLIC_KEY_PERMISSIONS=644
```

The private key is not included in this report or transmitted to the Pi.

## Installation result

The prior existing-key attempt was rejected. No already-authenticated Pi shell,
authorized password mechanism or management channel is available to install
the new public key.

```text
PI5_KEY_INSTALLATION=OWNER_CLAIMED_COMPLETE_KEY_AUTH_FAILED
PI5_KEY_AUTH=FAILED
PI5_SHELL=UNAVAILABLE
PI5_AUTH_METHOD=DEDICATED_SCOPE05_SSH_KEY_REJECTED
USB_DIAG_HOST=RASPBERRY_PI_5_PENDING_KEY_INSTALLATION
PI5_USB_ENUMERATION=NOT_COLLECTED
PI5_SERIAL_NODE=NOT_COLLECTED
PI5_CP2102_DRIVER_STATE=NOT_COLLECTED
NEXT_GATE=PI5_AUTONOMOUS_USB_HOST_DIAGNOSIS
FLASH_GATE=BLOCKED
```

## Exact one-time bootstrap command

This command is for an already logged-in local Pi shell as `pitan`; it does
not contain a password and was not executed by Codex:

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh && printf '%s\n' 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIY5mrT6alKz36Ds35SpROakabLU9zwUZaJn+925u5U8 scope05-pi5-automation' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
```

Validation after the Owner-reported bootstrap still returned
`PERMISSION_DENIED_PUBLICKEY`. No USB command has been run on the PC as a
substitute for Pi evidence. Key installation/reconciliation remains the next
gate.

Client-side reconciliation now confirms the existing dedicated key is valid,
matches its public half, and was offered to the server. The server rejected
that offered key.

```text
LOCAL_PRIVATE_PUBLIC_MATCH=yes
LOCAL_PUBLIC_FINGERPRINT_MATCH=yes
EXPECTED_KEY_OFFERED=yes
SERVER_ACCEPTED_KEY=no
PI5_KEY_RECONCILIATION=FAILED_SERVER_SIDE_KEY_INSTALLATION_REQUIRES_RECONCILIATION
```
