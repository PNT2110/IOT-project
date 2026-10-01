# SCOPE-05 USB Power Sanity Report

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## Auto-only canonical state

The later `OWNER_POLICY=AUTO_ONLY_NO_OWNER_INTERACTION` supersedes the
owner-assisted measurement state for current automation decisions. The earlier
Owner-reported `3.31 V` remains historical evidence only and is not treated as
a machine-readable sensor result.

```text
USB_POWER_SANITY_CHECK=AUTO_ONLY
BOARD_POWER_LED=UNAVAILABLE_NO_MACHINE_READABLE_SENSOR
V_3V3=UNAVAILABLE_NO_MACHINE_READABLE_SENSOR
V_5V=UNAVAILABLE_NO_MACHINE_READABLE_SENSOR
BOARD_3V3_POWER_PATH=UNVERIFIED_NO_MACHINE_READABLE_SENSOR
```

## Owner authorization (historical)

```text
OWNER_DECISION=AUTHORIZE_SCOPE05_USB_POWER_SANITY_CHECK
MULTIMETER_AVAILABLE=yes
PROPS_REMOVED_OR_PHYSICALLY_ISOLATED=yes
ESC_MOTOR_POWER_DISCONNECTED=yes
NO_LIPO_OR_HIGH_POWER_MOTOR_SUPPLY=yes
BOARD_POWERED_FROM_USB_ONLY=yes
MEASUREMENT_SCOPE=DC_GND_TO_LABELLED_3V3_ONLY
```

The bounded physical measurement was previously supplied by the Owner and is
retained only as historical evidence. No new machine-readable measurement is
available under the current auto-only policy. No USB data-line, arbitrary IC
pin, continuity, resistance, serial or firmware operation was performed.

## Observations and measurements

```text
BOARD_POWER_LED=ON
V_3V3=3.31
V_5V=SKIPPED_NO_SAFE_LABEL
BOARD_3V3_POWER_PATH=PASS_OWNER_MEASURED
```

The supplied photos show a `GND` label and a `3V3` label. They do not show an
unambiguous `5V`, `VIN` or `USB5V` measurement point, so no 5V probe is
requested.

## Owner measurement procedure

1. Keep LiPo/motor/ESC power disconnected and connect only USB-C.
2. Set the multimeter to DC volts.
3. Put the black probe on the clearly labelled `GND` pin.
4. Touch the red probe only to the clearly labelled `3V3` pin.
5. Report the board power/status LED state and the displayed voltage without
   rounding it into a more precise value.

```text
OWNER_MEASUREMENT_STATUS=COMPLETED_HISTORICAL_SUPERSEDED_BY_AUTO_ONLY
EVIDENCE_CLASS=OWNER_MEASURED_HISTORICAL
```

## Retained runtime state

```text
USB_PHYSICAL_ENUMERATION=FAIL_NO_EVENT
TTY_NODE=NOT_PRESENT
VID_PID=NOT_DETECTED
NEXT_DOMAIN=PHYSICAL_USB_PATH_REQUIRES_SCHEMATIC_OR_MACHINE_READABLE_INSTRUMENTATION
FLASH_GATE=BLOCKED
```

The Owner-reported `3.31 V` was within a normal 3.3 V rail range, but the
current auto-only policy does not use human measurements as current machine
readable evidence.

```text
PI5_AUTOMATION_KEY_FINGERPRINT=SHA256:VrUiXWY9kkxBKt+BwjXv6NMBtsUxOl8kxBXR+rv46i4
PI5_KEYPAIR_PREPARED=yes
PI5_KEY_INSTALLATION=BLOCKED_REQUIRES_ONE_TIME_OWNER_BOOTSTRAP
PI5_USB_EVIDENCE=NOT_COLLECTED
FLASH_GATE=BLOCKED
```
