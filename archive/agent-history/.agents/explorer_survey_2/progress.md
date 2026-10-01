# Progress Heartbeat - Survey Explorer 2 (USB Auto-Detect)

- **Status**: Deep investigation complete, authoring analysis.md and handoff.md
- **Last visited**: 2026-09-09T13:12:00Z
- **Current Step**: Drafting comprehensive architecture report (`analysis.md`) and 5-component handoff report (`handoff.md`)
- **Key Findings Synthesized**:
  1. Identified why VID/PID (both 0x1A86:0x7523 for CH340) and `/dev/serial/by-id` fail when two CH340 chips lack unique serial numbers.
  2. Identified physical topology limitations of `/dev/serial/by-path` in field drone operations.
  3. Formulated content-based detection: NMEA ($GN..., XOR checksum) at 38400 baud vs JSONL/ESP-IDF logs at 115200 baud.
  4. Discovered critical hardware gotcha: DTR/RTS auto-reset circuit on ESP32 devkits; opened ports must assert `dtr=False, rts=False` during probing to avoid inadvertent microcontroller resets.
  5. Designed centralized `UsbPortCoordinator` architecture to eliminate race conditions between worker threads.
  6. Designed portable `MockSerial` pytest simulation pattern that runs seamlessly on both Windows and Linux without requiring OS-specific `pty`.
