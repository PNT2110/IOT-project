# SCOPE-04 Camera Inventory

**STATUS: `CAMERA_INVENTORY=PASS`**  
**Captured:** 2026-09-24 (Asia/Ho_Chi_Minh)  
**Target:** Raspberry Pi 5 Model B Rev 1.0, hostname `pitan`  
**Access:** Existing owner-approved SSH path; read-only inventory only.

## Evidence

| Item | Result | Evidence class | Limitation/redaction |
|---|---|---|---|
| Device identity | Raspberry Pi 5 Model B Rev 1.0; kernel `6.18.50+rpt-rpi-2712`; hostname `pitan` | `CODEX_OBSERVED_READ_ONLY` | No credential or unnecessary host data stored. |
| Camera capture node | `/dev/video0`, `crw-rw----+`, owner `root`, group `video` | `CODEX_OBSERVED_READ_ONLY` | ACL details not expanded. |
| Camera metadata node | `/dev/video1`, `crw-rw----+`, owner `root`, group `video` | `CODEX_OBSERVED_READ_ONLY` | Metadata only; not an image capture node. |
| Camera/device name | `USB Composite Device: USB Camer` | `CODEX_OBSERVED_READ_ONLY` | Exact raw USB serial was empty/not retained. |
| Driver/bus | `uvcvideo`; `usb-xhci-hcd.1-1` | `CODEX_OBSERVED_READ_ONLY` | No unnecessary topology identifiers retained. |
| USB class correlation | Jieli USB Composite Device, relevant USB/bus class | `CODEX_OBSERVED_READ_ONLY` | Raw unrelated USB devices and unnecessary identifiers omitted. |
| `/dev/video0` capability | Video Capture, Streaming, Extended Pix Format; `640x480` YUYV at `30 fps` observed read-only | `CODEX_OBSERVED_READ_ONLY` | No frame was opened, captured or saved. |
| `/dev/video1` capability | Metadata Capture, Streaming, Extended Pix Format | `CODEX_OBSERVED_READ_ONLY` | No frame was opened, captured or saved. |
| Pi multimedia nodes | `/dev/video19` HEVC decoder; `/dev/video20`–`/dev/video35` PISP backend nodes | `CODEX_OBSERVED_READ_ONLY` | Treated as platform nodes, not external camera devices. |
| Project-account access path | `v4l2-ctl --all` returned device metadata successfully for `/dev/video0` and `/dev/video1` under account `pitan` | `CODEX_OBSERVED_READ_ONLY` | This proves metadata access, not streaming suitability or application performance. |

## Commands used

```text
hostname
uname -r
cat /proc/device-tree/model
ls -l /dev/video*
cat /sys/class/video4linux/video*/name
command -v v4l2-ctl
lsusb
v4l2-ctl --list-devices
v4l2-ctl --all -d /dev/video0
v4l2-ctl --all -d /dev/video1
```

`v4l2-ctl` was already installed. No package installation, permission change, service restart, network change, stream open, frame capture, firmware/ESP32/GNSS access or public exposure occurred.

## SCOPE-04 implication

The external USB UVC camera is sufficiently identified for a future SCOPE-04 adapter design. The implementation must still use an authenticated local stream, typed unavailable/error states, resource limits and no persistence by default. Supported formats observed here are inventory evidence only; no performance or application acceptance is claimed.

```text
CAMERA_INVENTORY=PASS
CAMERA_RECORDING_DEFAULT=off
CAMERA_FRAME_PERSISTENCE_DEFAULT=none
SCOPE04_IMPLEMENTATION_AT_INVENTORY_TIME=NOT_STARTED
CURRENT_IMPLEMENTATION_STATUS=SEE_SCOPE04_FINAL_REPORT_CURRENT
```
