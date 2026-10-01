# SCOPE-05 ESP32 → Pi USB telemetry contract v1

The Pi receives newline-delimited JSON over the ESP32 USB serial connection.
The frame itself carries no command. The Pi's few command lines are listed in
the amendments below; there is no ARM, DISARM or motor command.

## Transport

- Linux device must be explicitly configured as `/dev/ttyUSB*`,
  `/dev/ttyACM*`, or the stable CP2102 path
  `/dev/serial/by-id/usb-Silicon_Labs_CP210*`.
- The expected bridge is Silicon Labs CP2102/CP210x. The by-id path is
  preferred because `/dev/ttyUSB0` can change when USB devices are reordered.
- ESP USB output baud is `115200` (the GPS baud remains an ESP-side concern and
  is not the Pi USB baud).
- Maximum frame size is 16 KiB; one complete JSON object per line.
- The Pi rejects unknown schema, invalid numeric ranges, replayed sequence
  numbers and malformed UTF-8/JSON.

## Frame example

```json
{"schema_version":"scope05.esp32.usb.v1","seq":42,"imu":{"roll_deg":0.4,"pitch_deg":-1.2,"yaw_deg":18.0},"baro":{"altitude_m":12.3,"vertical_speed_mps":0.1,"temperature_c":31.2},"power":{"battery_pct":83.0,"voltage_v":15.7},"sbus":{"signal_ok":true,"channels":[1500,1500,1000,1500]},"gnss":{"fix_state":"VALID_FIX","latitude":10.0,"longitude":106.0,"altitude_m":12.1},"flight":{"arm_state":"DISARMED","mode":"ANGLE"},"pid":{"roll":{"kp":1.2,"ki":0.1,"kd":0.02}}}
```

The existing archived `FC_can_bang` source does not emit this frame yet;
`display.ino` contains only commented debug prints and no GNSS parser. Until
the firmware adds this read-only output, the Pi UI must show
`ESP_USB_NOT_CONFIGURED`/`ESP_USB_TIMEOUT` rather than invented measurements.

## Amendment 2026-10-01 — firmware emits this frame + Pi→ESP command lines

`firmware/FC_can_bang` now emits this frame every 200 ms (seq increments only
for frames actually sent; the Pi reads the newest line and counts skipped
frames in `device.dropped_frames`; an `uptime_ms` decrease is an ESP restart,
not a replay). Extra optional keys: `gnss.satellites/hdop/speed_mps/course_deg/
uart_rx_pin/detected`, `flight.authorization/auth_ref/auth_remaining_s/
arm_block_reason/max_altitude_m/altitude_limited/throttle_us/motors_us`,
`link.*`, `uptime_ms`, `imu.yaw_reference` (`GYRO_RELATIVE`, no compass).

The Pi may write (only when `UsbSerialLineReader(allow_commands=True)`, same fd):

| Line | Effect on ESP |
|---|---|
| `$AUTH,ALLOW,<1..86400>,<ref>*HH` | permits arming until expiry (RAM only) |
| `$AUTH,DENY,<ref>*HH` | blocks the next arm; never cuts motors in flight |
| `$PID,<roll|pitch|yaw|angle>,<kp>,<ki>,<kd>*HH` | rejected while ARMED |
| `$MAXALT,<2..500>*HH` | rejected while ARMED |
| `$PING*HH` | heartbeat |

`HH` = XOR of the bytes between `$` and `*` (NMEA style). There is no ARM,
DISARM or motor command: the pilot still arms with the RC switch, and the ESP
refuses unless authorization is live, RC is valid, mode is ANGLE, the switch
was seen in DISARM first and throttle is low. Implementation:
`edge/pi5/pi5/telemetry/esp_command.py`.

## Amendment 2026-10-01 (2) — flight-mode principle, Pi heartbeat, saved settings

- The ESP boots `BLOCKED`. Arming needs a live `$AUTH,ALLOW` **and** a `$PING`
  from the Pi within the last 10 s; the Pi sends `$PING` every 2 s.
- `flight.mode` is one of `BLOCKED`, `ANGLE`, `KILL`, `FAILSAFE`.
- `flight.arm_block_reason` while disarmed, highest priority first: `RC_LOST`,
  `NO_FLIGHT_AUTHORIZATION`, `PI_LINK_LOST`, `NO_GPS_FIX`, `MODE_NOT_ANGLE`,
  `ARM_SWITCH_NOT_RESET`, `THROTTLE_HIGH`, `ARM_SWITCH_LOW` (ready; waiting for
  the pilot's switch). After a disarm it is `DISARMED_BY_SWITCH`,
  `FAILSAFE_RC_LOST` or `KILL_MODE` until the next evaluation.
- In flight only the arm switch, RC loss (including the SBUS failsafe flag) or
  KILL mode stop the motors. An expired or revoked authorization, or a lost Pi,
  blocks the next arm and never cuts motors in the air.
- Above `max_altitude_m` (relative to the arming point) the throttle ceiling
  latches 30 us under the current throttle and eases down 10 us/s until the
  aircraft is 1 m below the limit.
- `$PID` and `$MAXALT` values are stored in NVS and restored at boot.
- `link.pi_alive` reports the heartbeat state.
- GPS: UART1, RX on GPIO16 (probes GPIO17 if no valid NMEA arrives), 38400 8N1,
  NMEA 0183 v4.0/4.1, receive-only (no TX pin is driven, no UBX is sent).

Logic under test on the host: `firmware/FC_can_bang/flight_gate.h`,
`tests/firmware/`.
