from __future__ import annotations

import sys
from pathlib import Path


PI_ROOT = Path(__file__).resolve().parents[2] / "edge" / "pi5"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))
