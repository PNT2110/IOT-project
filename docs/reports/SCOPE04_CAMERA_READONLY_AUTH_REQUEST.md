# SCOPE-04 Camera Read-Only Inventory Authorization Request

**STATUS: `GRANTED — INVENTORY_COMPLETED`**  
**Target:** Owner-identified Raspberry Pi 5, hostname `pitan`; re-confirm device identity through the approved access path before execution.

## Purpose and boundary

Authorize one bounded, read-only camera inventory for SCOPE-04 readiness. This request does not authorize camera streaming, frame capture, networking changes, package installation, service changes, reboot, firmware/ESP32/GNSS work or SCOPE-04 implementation.

## Proposed access and facts

Use an existing owner-approved remote/local access path only after the target identity is confirmed. Codex may collect only:

```bash
ls -l /dev/video*
cat /sys/class/video4linux/video*/name
```

If `v4l2-ctl` is already installed, the following may be added only within the same approval:

```bash
v4l2-ctl --list-devices
v4l2-ctl --all -d <verified device>
```

An approved read-only `lsusb` may identify the relevant USB/bus class. Do not install `v4l-utils`, open a stream or record an image merely for inventory.

## Output handling

Store only device nodes, driver/device name, relevant USB/bus class, permissions/group ownership, whether the project user can open the device, and read-only supported formats/modes if available. Redact serials and unnecessary identifiers. Do not store raw logs or images.

## Owner approval block

```text
CAMERA_READONLY_INVENTORY_AUTHORIZATION=GRANT / DENY
TARGET_DEVICE_CONFIRMATION=Raspberry Pi 5 / hostname pitan / correct device
APPROVED_ACCESS_METHOD:
APPROVED_TIME_WINDOW:
OUTPUT_REDACTION_AND_STORAGE_LOCATION:
NO_NETWORK_CHANGE=yes
NO_PACKAGE_INSTALL=yes
NO_CAMERA_STREAM_OR_FRAME_CAPTURE=yes
NO_FIRMWARE_OR_ESP32_GNSS_WORK=yes
```

The owner accepted the proposal with `OWNER_DECISION=ACCEPT_THIS_PROPOSAL`; the bounded inventory was executed and is recorded in [SCOPE04_CAMERA_INVENTORY.md](SCOPE04_CAMERA_INVENTORY.md).

```text
CAMERA_READONLY_INVENTORY_AUTHORIZATION=GRANT
CAMERA_INVENTORY=PASS
NO_NETWORK_CHANGE=yes
NO_PACKAGE_INSTALL=yes
NO_CAMERA_STREAM_OR_FRAME_CAPTURE=yes
```
