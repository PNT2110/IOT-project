"""Compile and run the firmware's pure-C++ logic on the host."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "firmware" / "FC_can_bang"


def _compiler() -> str | None:
    found = shutil.which("g++")
    if found:
        return found
    strawberry = Path("C:/Strawberry/c/bin/g++.exe")
    return str(strawberry) if strawberry.exists() else None


@pytest.mark.parametrize("name", ["test_gps_nmea", "test_flight_gate"])
def test_firmware_host_logic(name: str, tmp_path: Path) -> None:
    compiler = _compiler()
    if compiler is None:
        pytest.skip("g++ is not installed")
    binary = tmp_path / (name + (".exe" if os.name == "nt" else ""))
    env = {**os.environ, "PATH": str(Path(compiler).parent) + os.pathsep + os.environ.get("PATH", "")}
    build = subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", f"-I{FIRMWARE}", str(Path(__file__).with_name(name + ".cpp")), "-o", str(binary)], capture_output=True, text=True, env=env)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, env=env, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all checks passed" in run.stdout
