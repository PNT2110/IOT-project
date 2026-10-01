#!/usr/bin/env python3
"""Read-only UART scanner for the BZ251. Stop iot-drone before running."""

from __future__ import annotations

import argparse
import time

import serial


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="/dev/serial0")
    parser.add_argument("--seconds", type=float, default=2.0)
    args = parser.parse_args()
    bauds = (9600, 19200, 38400, 57600, 115200, 230400, 460800)

    for baud in bauds:
        with serial.Serial(args.device, baud, timeout=0.2) as port:
            port.reset_input_buffer()
            deadline = time.monotonic() + args.seconds
            payload = bytearray()
            while time.monotonic() < deadline and len(payload) < 2048:
                payload.extend(port.read(256))
        sample = bytes(payload[:160])
        print(f"baud={baud:<6} bytes={len(payload):<4} sample={sample!r}")


if __name__ == "__main__":
    main()
