#!/usr/bin/env python3
"""Bounded, receive-only GNSS capture utility.

The utility is preparation only. It is not run by SCOPE-05 until the physical
UART and electrical gates pass. It has no transmit/configuration operation.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import time


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def capture(*, port: str, output: Path, duration: float, baudrate: int) -> int:
    if not 0 < duration <= 300:
        raise ValueError("duration must be within (0, 300] seconds")
    try:
        import serial  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on optional runtime
        raise RuntimeError("pyserial is required only when this tool is explicitly run") from exc

    deadline = time.monotonic() + duration
    with serial.Serial(
        port=port,
        baudrate=baudrate,
        timeout=0.2,
        write_timeout=0,
        rtscts=False,
        dsrdtr=False,
        exclusive=True,
    ) as device, output.open("w", encoding="utf-8") as stream:
        while time.monotonic() < deadline:
            chunk = device.read(device.in_waiting or 1)
            if chunk:
                stream.write(json.dumps({"captured_at": _timestamp(), "raw_b64": base64.b64encode(chunk).decode("ascii")}) + "\n")
                stream.flush()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="bounded GNSS receive-only capture; no TX/configuration")
    parser.add_argument("--port", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--baud", type=int, default=38400)
    args = parser.parse_args()
    return capture(port=args.port, output=args.output, duration=args.duration, baudrate=args.baud)


if __name__ == "__main__":
    raise SystemExit(main())
