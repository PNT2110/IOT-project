from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.ops import nearest_points

from .config import settings
from .models import GeofenceState, GpsFix


def haversine_m(a_lon: float, a_lat: float, b_lon: float, b_lat: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(a_lat), math.radians(b_lat)
    dphi = math.radians(b_lat - a_lat)
    dlambda = math.radians(b_lon - a_lon)
    value = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(value))


class GeofenceEngine:
    def __init__(self, path: Path | None = None):
        self.path = path or settings.zones_path
        self.zones: list[tuple[object, dict]] = []
        self.loaded_at: datetime | None = None

    def load(self) -> int:
        self.zones = []
        if not self.path.exists():
            return 0
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        for feature in payload.get("features", []):
            geometry = feature.get("geometry")
            if geometry:
                self.zones.append((shape(geometry), feature.get("properties", {})))
        self.loaded_at = datetime.now(timezone.utc)
        return len(self.zones)

    def evaluate(self, fix: GpsFix) -> GeofenceState:
        now = datetime.now(timezone.utc)
        if not self.zones or not fix.valid or fix.latitude is None or fix.longitude is None or fix.stale:
            return GeofenceState(data_ready=bool(self.zones), checked_at=now)
        point = Point(fix.longitude, fix.latitude)
        nearest: tuple[float, dict] | None = None
        for geometry, properties in self.zones:
            if geometry.covers(point):
                return GeofenceState(
                    status="breach",
                    zone_id=str(properties.get("id", "unknown")),
                    zone_name=str(properties.get("name", properties.get("rawName", "Vùng kiểm soát"))),
                    distance_m=0,
                    data_ready=True,
                    checked_at=now,
                )
            boundary_point = nearest_points(point, geometry)[1]
            distance = haversine_m(point.x, point.y, boundary_point.x, boundary_point.y)
            if nearest is None or distance < nearest[0]:
                nearest = (distance, properties)
        if nearest and nearest[0] <= settings.geofence_warning_m:
            return GeofenceState(
                status="warning",
                zone_id=str(nearest[1].get("id", "unknown")),
                zone_name=str(nearest[1].get("name", nearest[1].get("rawName", "Vùng kiểm soát"))),
                distance_m=round(nearest[0], 1),
                data_ready=True,
                checked_at=now,
            )
        return GeofenceState(status="safe", distance_m=round(nearest[0], 1) if nearest else None, data_ready=True, checked_at=now)


geofence = GeofenceEngine()

