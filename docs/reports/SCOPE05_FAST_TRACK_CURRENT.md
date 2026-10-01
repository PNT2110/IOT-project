# SCOPE-05 One-Prompt Fast-Track Current State

Assessment date: `2026-09-27` (Asia/Ho_Chi_Minh).

## Phase result

```text
MODE=FAST_TRACK_SINGLE_PROMPT
OWNER_POLICY=AUTO_ONLY_NO_OWNER_INTERACTION
CURRENT_USB_HOST=RASPBERRY_PI_5
PI5_HOST=192.168.1.118
PI5_USER=pitan
FLASH_GATE=BLOCKED
```

Phase 1 passed:

```text
LOCAL_PRIVATE_PUBLIC_MATCH=yes
LOCAL_PUBLIC_FINGERPRINT_MATCH=yes
```

Phase 2 failed. The dedicated key was offered, but the server rejected it:

```text
EXPECTED_KEY_OFFERED=yes
SERVER_ACCEPTED_KEY=no
SSH_FAILURE_STAGE=SERVER_REJECTED_PUBLIC_KEY
PI5_KEY_AUTH=FAILED
PI5_SHELL=UNAVAILABLE
```

## Phase 3 blocker

The one-shot remediation must run locally on the Pi as `pitan`; it cannot be
executed through the rejected SSH session. No password fallback was used.

```text
PI5_USB_EVIDENCE=NOT_COLLECTED
PI5_USB_ENUMERATION=NOT_COLLECTED
PI5_SERIAL_NODE=NOT_COLLECTED
PI5_CP2102_DRIVER_STATE=NOT_COLLECTED
NEXT_GATE=PI5_LOCAL_AUTHORIZED_KEYS_REPAIR
FLASH_GATE=BLOCKED
```

## Single permitted Pi-local command

Run in a local Pi terminal while logged in as `pitan`; this command was not
executed by Codex:

```bash
set -eu

U='pitan'
CLIENT_IP='192.168.1.47'
PUB='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIY5mrT6alKz36Ds35SpROakabLU9zwUZaJn+925u5U8 scope05-pi5-automation'

[ "$(id -un)" = "$U" ] || { echo "ERROR_WRONG_USER=$(id -un)"; exit 2; }

H="$(getent passwd "$U" | cut -d: -f6)"
G="$(id -gn "$U")"

echo "USER=$U"
echo "HOME=$H"

sudo install -d -m 700 -o "$U" -g "$G" "$H/.ssh"
sudo touch "$H/.ssh/authorized_keys"
sudo chown "$U:$G" "$H/.ssh/authorized_keys"
sudo chmod 600 "$H/.ssh/authorized_keys"
sudo chmod go-w "$H" || true

grep -qxF "$PUB" "$H/.ssh/authorized_keys" || \
  printf '%s\n' "$PUB" | sudo tee -a "$H/.ssh/authorized_keys" >/dev/null

echo '=== KEY MATCH ==='
grep -nF "$PUB" "$H/.ssh/authorized_keys"

echo '=== FINGERPRINTS ==='
ssh-keygen -lf "$H/.ssh/authorized_keys" || true

echo '=== PATH MODES ==='
namei -l "$H/.ssh/authorized_keys" || true
stat -c '%U:%G %a %n' "$H" "$H/.ssh" "$H/.ssh/authorized_keys"

echo '=== EFFECTIVE SSHD POLICY ==='
sudo sshd -T -C user="$U",host="$(hostname)",addr="$CLIENT_IP" | \
grep -Ei '^(pubkeyauthentication|authorizedkeysfile|authorizedkeyscommand|strictmodes|authenticationmethods|allowusers|denyusers|passwordauthentication|kbdinteractiveauthentication)'

echo '=== RECENT SSH AUTH LOG ==='
sudo journalctl -u ssh -n 120 --no-pager 2>/dev/null | \
grep -Ei 'sshd|publickey|authorized|authentication|pitan|failed|refused|bad ownership|bad modes' || true

echo '=== SSHD CONFIG TEST ==='
sudo sshd -t
echo 'SSHD_CONFIG_TEST=PASS'
```

No USB/CP2102 phase was run because SSH did not pass. Existing historical PC
USB evidence remains non-authoritative for the Pi attachment.

## Additional local-session audit

After the key rejection, the orchestration environment was checked for a
pre-existing path that could run the Pi-local repair without credentials:

```text
PI5_UI_SESSION=NOT_PRESENT
PI5_SSH_CONTROL_SOCKET=NOT_PRESENT
PI5_SSH_TCP_SESSION=NOT_PRESENT
PI5_LOCAL_TERMINAL_SESSION=NOT_PRESENT
```

No safe alternate channel exists in the current execution context. The blocker
is external-state dependent: the one-shot command must execute on the Pi-local
shell before dedicated SSH can be retried successfully.

## Latest verified Pi-side result

An explicitly supplied Owner password was used for one native SSH session after
the dedicated-key failure. The remote host was verified as Pi 5 and USB
inventory was collected directly there. The password was not stored in any
report.

```text
PI5_KEY_AUTH=FAILED
PI5_PASSWORD_AUTH=PASS
PI5_SHELL=AVAILABLE
PI5_AUTH_METHOD=OWNER_SUPPLIED_PASSWORD
USB_DIAG_HOST=RASPBERRY_PI_5
PI5_MODEL=Raspberry Pi 5 Model B Rev 1.0
PI5_USB_ENUMERATION=PASS
PI5_SERIAL_NODE=PASS
PI5_CP2102_DRIVER_STATE=BOUND
PI5_TTY_NODE=/dev/ttyUSB0
PI5_VID_PID=10c4:ea60
PI5_USB_PRODUCT=CP2102_USB_to_UART_Bridge_Controller
PI5_USB_MANUFACTURER=Silicon_Labs
PI5_PASSIVE_USB_EVENT=NONE_OBSERVED
NEXT_GATE=PI5_READ_ONLY_ESP_IDENTITY
FLASH_GATE=BLOCKED
```

The bounded observer saw only unrelated PWM events during its 60-second
window; the CP2102 was already present and bound. No serial port was opened.

## 2026-09-27 FAST TRACK continuation

The USB blocker was not reopened. From the verified Pi 5 endpoint, tty
exclusivity was checked and no owner was found. A temporary isolated esptool
5.4.0 environment was used for read-only `chip-id`, `read-mac` and `flash-id`.
All three operations exited 0; raw MAC output is redacted.

```text
PI5_USB_ENUMERATION=PASS
PI5_SERIAL_NODE=PASS
PI5_CP2102_DRIVER_STATE=BOUND
PI5_TTY_NODE=/dev/ttyUSB0
ESP_IDENTITY=PASS_READ_ONLY
ESP_CHIP_FAMILY=ESP32
ESP_CHIP_MODEL=ESP32-D0WD-V3
ESP_CHIP_REVISION=v3.1
FLASH_SIZE=4MB
BUILD_SYSTEM=NONE_FOUND
BUILD_TARGET_USED=NONE
BUILD_RESULT=BLOCKED
SOURCE_PINMAP_COMPATIBILITY=PARTIAL_SOURCE_ONLY
GNSS_UART_CANDIDATES=UNASSIGNED
GNSS_UART_SELECTED=NONE
LOGIC_POWER_COMPATIBILITY=BLOCKED
GNSS_INTEGRATION_PATCH=NOT_PREPARED
NEXT_GATE=BUILD_TARGET_RECONCILIATION_AND_GNSS_HARDWARE_EVIDENCE
FLASH_GATE=BLOCKED
```

No firmware source was modified, no build was guessed or compiled, and no
GNSS/motor/ESC/ARM/DISARM operation was performed.

## 2026-09-27 MEGA FAST TRACK continuation

```text
PI5_KEY_AUTH=PASS
ESP_IDENTITY=PASS_READ_ONLY
BUILD_TOOLCHAIN=BLOCKED_FRAMEWORK_INSTALL_ERRNO_28
BUILD_ORIGINAL_RESULT=BLOCKED_BEFORE_COMPILE
BUILD_GNSS_DISABLED_RESULT=BLOCKED_SAME_TOOLCHAIN_DEPENDENCY
GNSS_DATASHEET_STATUS=CONFLICTING_VENDOR_PAGE_AND_DATASHEET_MIRROR
GNSS_UART_CANDIDATES=UART0_OR_GPIO_MATRIX_CANDIDATES_UNVERIFIED
GNSS_UART_SELECTED=NONE
LOGIC_POWER_COMPATIBILITY=PARTIAL_ELECTRICAL_EVIDENCE_PHYSICAL_WIRING_UNVERIFIED
GNSS_INTEGRATION_PATCH=PREPARED_DISABLED_BY_DEFAULT_REPO_BOUNDARY
GNSS_READ_ONLY_CAPTURE_TOOL=PREPARED_NOT_RUN
GNSS_LIVE_CAPTURE=BLOCKED
NEXT_GATE=BUILD_COMPATIBILITY_FIX
FLASH_GATE=BLOCKED
```
