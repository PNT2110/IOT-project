from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv("DRONE_DATA_DIR", "./data"))
    static_dir: Path = Path(os.getenv("DRONE_STATIC_DIR", "../frontend/dist"))
    gps_device: str = os.getenv("GPS_DEVICE", "auto")
    gps_baud: int = int(os.getenv("GPS_BAUD", "38400"))
    esp_device: str = os.getenv("ESP_DEVICE", "auto")
    esp_baud: int = int(os.getenv("ESP_BAUD", "115200"))
    serial_probe_timeout: float = float(os.getenv("SERIAL_PROBE_TIMEOUT", "1.0"))
    cookie_secure: bool = _bool("COOKIE_SECURE", False)
    session_hours: int = int(os.getenv("SESSION_HOURS", "8"))
    enable_real_flight_commands: bool = _bool("ENABLE_REAL_FLIGHT_COMMANDS", False)
    geofence_warning_m: float = float(os.getenv("GEOFENCE_WARNING_M", "100"))
    gps_stale_seconds: float = float(os.getenv("GPS_STALE_SECONDS", "5"))
    retention_days: int = int(os.getenv("RETENTION_DAYS", "30"))
    retention_bytes: int = int(os.getenv("RETENTION_BYTES", str(5 * 1024**3)))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "drone.sqlite3"

    @property
    def zones_path(self) -> Path:
        return self.data_dir / "zones.geojson"

    @property
    def map_path(self) -> Path:
        return self.data_dir / "maps" / "hcm.pmtiles"


settings = Settings()

