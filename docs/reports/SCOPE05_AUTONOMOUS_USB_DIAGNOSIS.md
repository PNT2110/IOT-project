# SCOPE-05 Autonomous USB Diagnosis

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## Auto-only policy

```text
OWNER_POLICY=AUTO_ONLY_NO_OWNER_INTERACTION
HUMAN_MEASUREMENT_REQUESTS=DISABLED
HUMAN_HOTPLUG_REQUESTS=DISABLED
HUMAN_BUTTON_PRESS_REQUESTS=DISABLED
```

No Owner interaction was requested. No USB retry, serial open/write, driver
installation, firmware operation, GNSS configuration or motor action occurred.

## Machine-readable collection

Snapshot window:

```text
SNAPSHOT_START=2026-09-26T20:14:48+07:00
SNAPSHOT_POST_OBSERVER=2026-09-26T20:15:58+07:00
HOST_KERNEL=7.0.0-34-generic
USB_CONTROLLER=Intel Alder Lake-S PCH USB 3.2 xHCI, driver xhci_hcd
```

Observed USB devices were the Linux root hubs, Apple keyboard/dongle, Logitech
mouse and Genesys Logic hub. No CP2102/CP210x, ESP32, USB-serial or new board
device was visible in `lsusb` or `lsusb -t`.

```text
USB_DEVICE_ENUMERATION=NO_CP210X_OR_BOARD_DEVICE
TTY_USB=NOT_PRESENT
TTY_ACM=NOT_PRESENT
DEV_SERIAL=NOT_PRESENT
```

The `cp210x` kernel module metadata exists locally, but no device reached the
USB descriptor/driver-binding stage. No module reload or installation was
attempted.

## Passive observer

```text
OBSERVER=udevadm monitor --kernel --udev --property
OBSERVER_WINDOW=55_SECONDS
OBSERVER_EXIT=TIMEOUT_124
USB_ADD_EVENT=NOT_OBSERVED
USB_REMOVE_EVENT=NOT_OBSERVED
TTY_EVENT=NOT_OBSERVED
USB_ERROR_EVENT=NOT_OBSERVED
```

## Classification

```text
AUTO_USB_RESULT=NO_DEVICE_NO_EVENT
AUTO_DIAG_LIMIT=PHYSICAL_LAYER_NOT_MACHINE_OBSERVABLE
DRIVER_DIAGNOSIS=NOT_REACHED_DEVICE_DID_NOT_ENUMERATE
ELECTRICAL_MEASUREMENT=UNAVAILABLE_AUTONOMOUSLY
BOARD_POWER_LED=UNAVAILABLE_NO_MACHINE_READABLE_SENSOR
V_3V3=UNAVAILABLE_NO_MACHINE_READABLE_SENSOR
V_5V=UNAVAILABLE_NO_MACHINE_READABLE_SENSOR
BOARD_3V3_POWER_PATH=UNVERIFIED_NO_MACHINE_READABLE_SENSOR
NEXT_BLOCKER=PHYSICAL_USB_PATH_REQUIRES_SCHEMATIC_OR_MACHINE_READABLE_INSTRUMENTATION
FLASH_GATE=BLOCKED
```

This evidence does not identify a failing cable, connector, CP2102, regulator
or board power path. It only establishes that this PC could not observe the
board as a USB device during the automatic window.
