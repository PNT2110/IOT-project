from __future__ import annotations

import json
import math
from typing import Any

from shapely.geometry import shape


class GeometryError(ValueError):
    pass


def validate_polygon_geojson(value: dict[str, Any], max_bytes: int = 200_000) -> dict[str, Any]:
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except RecursionError as exc:
        raise GeometryError("geometry nesting is too deep") from exc
    if len(encoded.encode("utf-8")) > max_bytes:
        raise GeometryError("geometry exceeds size limit")
    if value.get("type") not in {"Polygon", "MultiPolygon"}:
        raise GeometryError("only Polygon or MultiPolygon is accepted")
    if "crs" in value:
        raise GeometryError("GeoJSON CRS member is not accepted; coordinates are WGS84")
    coordinates = value.get("coordinates")
    if coordinates is None:
        raise GeometryError("coordinates are required")

    def walk(item: Any) -> None:
        if isinstance(item, (int, float)):
            if not math.isfinite(item):
                raise GeometryError("coordinates must be finite")
            return
        if not isinstance(item, list) or not item:
            raise GeometryError("coordinates must be non-empty arrays")
        for child in item:
            walk(child)

    try:
        walk(coordinates)
    except RecursionError as exc:
        raise GeometryError("geometry nesting is too deep") from exc
    try:
        geometry = shape(value)
    except Exception as exc:  # shapely gives implementation-specific exceptions
        raise GeometryError("invalid geometry") from exc
    if geometry.is_empty or not geometry.is_valid:
        raise GeometryError("geometry must be non-empty and valid")
    if not geometry.geom_type in {"Polygon", "MultiPolygon"}:
        raise GeometryError("geometry type mismatch")
    if geometry.bounds[0] < -180 or geometry.bounds[2] > 180 or geometry.bounds[1] < -90 or geometry.bounds[3] > 90:
        raise GeometryError("coordinates outside WGS84 bounds")
    return value


PUBLIC_FIXTURE = {
    "type": "Polygon",
    "coordinates": [[[10.0, 10.0], [10.2, 10.0], [10.2, 10.2], [10.0, 10.2], [10.0, 10.0]]],
}
INTERNAL_FIXTURE = {
    "type": "Polygon",
    "coordinates": [[[20.0, 20.0], [20.2, 20.0], [20.2, 20.2], [20.0, 20.2], [20.0, 20.0]]],
}
