# SCOPE-05 Pi 5 Key Installation Reconciliation

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## Client-side key integrity

```text
LOCAL_PRIVATE_PUBLIC_MATCH=yes
LOCAL_PUBLIC_FINGERPRINT_MATCH=yes
PI5_AUTOMATION_KEY_FINGERPRINT=SHA256:VrUiXWY9kkxBKt+BwjXv6NMBtsUxOl8kxBXR+rv46i4
CLIENT_KEY_PATH=PASS
```

The existing dedicated key is valid and was not regenerated.

## Verbose authentication result

```text
SSH_TARGET=pitan@192.168.1.118
EXPECTED_KEY_OFFERED=yes
SERVER_ACCEPTED_KEY=no
SSH_FAILURE_STAGE=SERVER_REJECTED_PUBLIC_KEY
PI5_KEY_AUTH=FAILED
```

The server identifies as OpenSSH on the reachable target and offers
`publickey,password`. The dedicated key was explicitly offered, then the
server continued authentication without accepting it. Password and
keyboard-interactive fallback were disabled.

## Root-cause classification

```text
PI5_KEY_RECONCILIATION=FAILED_SERVER_SIDE_KEY_INSTALLATION_REQUIRES_RECONCILIATION
LIKELY_DOMAINS=AUTHORIZED_KEYS_OR_ACCOUNT_HOME_OR_PERMISSIONS_OR_SSHD_POLICY
PI5_SHELL=UNAVAILABLE
PI5_USB_EVIDENCE=NOT_COLLECTED
NEXT_GATE=PI5_LOCAL_AUTHORIZED_KEYS_RECONCILIATION
FLASH_GATE=BLOCKED
```

The evidence rules out a local private/public mismatch and shows that the
client offered the expected key. It cannot distinguish absent key, wrong home,
ownership/permissions or sshd policy without an authenticated Pi-local check.

## Exact Pi-local reconciliation command

Run only while locally logged in as `pitan` on the Pi. It refuses a different
account and does not contain a password. Codex did not execute it remotely:

```bash
set -eu

EXPECTED_USER='pitan'
PUBKEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIY5mrT6alKz36Ds35SpROakabLU9zwUZaJn+925u5U8 scope05-pi5-automation'

ACTUAL_USER="$(id -un)"

if [ "$ACTUAL_USER" != "$EXPECTED_USER" ]; then
  echo "ERROR: logged in as $ACTUAL_USER; expected $EXPECTED_USER"
  exit 2
fi

HOME_DIR="$(getent passwd "$EXPECTED_USER" | cut -d: -f6)"

if [ -z "$HOME_DIR" ] || [ ! -d "$HOME_DIR" ]; then
  echo "ERROR: cannot resolve home for $EXPECTED_USER"
  exit 3
fi

umask 077
mkdir -p "$HOME_DIR/.ssh"
touch "$HOME_DIR/.ssh/authorized_keys"
chmod 700 "$HOME_DIR/.ssh"
chmod 600 "$HOME_DIR/.ssh/authorized_keys"
chown "$EXPECTED_USER":"$(id -gn)" "$HOME_DIR/.ssh"
chown "$EXPECTED_USER":"$(id -gn)" "$HOME_DIR/.ssh/authorized_keys"

if ! grep -qxF "$PUBKEY" "$HOME_DIR/.ssh/authorized_keys"; then
  printf '%s\n' "$PUBKEY" >> "$HOME_DIR/.ssh/authorized_keys"
fi

echo "USER=$(id -un)"
echo "HOME=$HOME_DIR"
stat -c 'SSH_DIR=%U:%G %a %n' "$HOME_DIR/.ssh"
stat -c 'AUTHORIZED_KEYS=%U:%G %a %n' "$HOME_DIR/.ssh/authorized_keys"
grep -nF "$PUBKEY" "$HOME_DIR/.ssh/authorized_keys" || true
ssh-keygen -lf "$HOME_DIR/.ssh/authorized_keys" || true
```

No sshd configuration change or restart is authorized in this scope.

## Current execution result

The local Pi reconciliation script could not be executed because no
authenticated Pi shell is available. A fresh key-only retry still returned
`PERMISSION_DENIED_PUBLICKEY`.

```text
PI5_LOCAL_USER=NOT_COLLECTED
PI5_HOME=NOT_COLLECTED
AUTHORIZED_KEY_EXACT_MATCH=NOT_COLLECTED
AUTHORIZED_KEY_FINGERPRINT_MATCH=NOT_COLLECTED
SSH_DIR_OWNER_MODE=NOT_COLLECTED
AUTHORIZED_KEYS_OWNER_MODE=NOT_COLLECTED
SSHD_PUBKEYAUTH=NOT_COLLECTED
PI5_KEY_AUTH=FAILED
NEXT_GATE=PI5_LOCAL_AUTHORIZED_KEYS_RECONCILIATION_REQUIRES_PI_LOCAL_EXECUTION
FLASH_GATE=BLOCKED
```

## Fast-track result

The one-pass fast-track retry and its single verbose confirmation produced the
same server-side rejection. The key was offered, but not accepted; no Pi-local
USB command was run.

```text
FAST_TRACK_SSH_RETRY=FAILED
EXPECTED_KEY_OFFERED=yes
SERVER_ACCEPTED_KEY=no
PI5_KEY_AUTH=FAILED
PI5_SHELL=UNAVAILABLE
NEXT_GATE=PI5_SSHD_POLICY_RECONCILIATION
FLASH_GATE=BLOCKED
```
