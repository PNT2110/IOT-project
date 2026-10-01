from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import httpx
import mapbox_vector_tile
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from .config import settings
from .db import db

SOURCE = "https://cambay.mod.gov.vn"
TILE_ZOOM = 9
HCM_BOXES = [
    (106.30, 10.30, 107.65, 11.65),  # TPHCM + Bình Dương + Bà Rịa-Vũng Tàu cũ, kèm buffer
    (106.45, 8.55, 106.85, 8.85),    # Côn Đảo, kèm buffer
]
ZONE_TYPES = {1: "prohibited", 2: "restricted"}


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    n = 2**zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_coordinates() -> list[tuple[int, int, int]]:
    tiles: set[tuple[int, int, int]] = set()
    for min_lon, min_lat, max_lon, max_lat in HCM_BOXES:
        min_x, max_y = lonlat_to_tile(min_lon, min_lat, TILE_ZOOM)
        max_x, min_y = lonlat_to_tile(max_lon, max_lat, TILE_ZOOM)
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                tiles.add((TILE_ZOOM, x, y))
    return sorted(tiles)


def _tile_point_to_lonlat(x: float, y: float, z: int, tile_x: int, tile_y: int, extent: int) -> tuple[float, float]:
    """Convert decoder coordinates (origin at tile bottom-left) to WGS84."""
    n = 2**z
    world_x = tile_x + (x / extent)
    world_y = tile_y + ((extent - y) / extent)
    lon = world_x / n * 360.0 - 180.0
    mercator = math.pi * (1 - 2 * world_y / n)
    lat = math.degrees(math.atan(math.sinh(mercator)))
    return lon, lat


def _transform_coordinates(value, z: int, tile_x: int, tile_y: int, extent: int):
    if isinstance(value, (list, tuple)) and len(value) >= 2 and all(isinstance(v, (int, float)) for v in value[:2]):
        return _tile_point_to_lonlat(float(value[0]), float(value[1]), z, tile_x, tile_y, extent)
    return [_transform_coordinates(item, z, tile_x, tile_y, extent) for item in value]


def sync_zones(output: Path | None = None) -> dict:
    output = output or settings.zones_path
    headers = {"User-Agent": "IOT-Drone-Station/0.1 (+local safety cache)"}
    # The official vector tiles currently identify prohibited/restricted layers
    # as 1 and 2. Merge clipped pieces by source id so no per-feature API crawl
    # is needed and the stored snapshot remains bounded to the HCMC region.
    pieces: dict[tuple[str, int], list] = {}
    with httpx.Client(timeout=30, headers=headers, follow_redirects=True) as client:
        for z, x, y in tile_coordinates():
            response = client.get(f"{SOURCE}/api/tiles/features/{z}/{x}/{y}.pbf")
            response.raise_for_status()
            decoded = mapbox_vector_tile.decode(response.content)
            layer = decoded.get("features", {})
            extent = int(layer.get("extent", 4096))
            for feature in layer.get("features", []):
                properties = feature.get("properties", {})
                layer_id = int(properties.get("layer_id", 0))
                if layer_id not in ZONE_TYPES:
                    continue
                feature_id = properties.get("id") or feature.get("id")
                geometry = feature.get("geometry")
                if feature_id is None or not geometry:
                    continue
                geometry = dict(geometry)
                geometry["coordinates"] = _transform_coordinates(geometry["coordinates"], z, x, y, extent)
                candidate = shape(geometry)
                if not candidate.is_empty:
                    pieces.setdefault((str(feature_id), layer_id), []).append(candidate)

    features: list[dict] = []
    for (feature_id, layer_id), geometries in sorted(pieces.items()):
        merged = unary_union(geometries)
        if not merged.is_valid:
            merged = merged.buffer(0)
        if merged.is_empty:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(merged),
                "properties": {
                    "id": feature_id,
                    "layer_id": layer_id,
                    "zone_type": ZONE_TYPES[layer_id],
                    "source": SOURCE,
                },
            }
        )

    collection = {
        "type": "FeatureCollection",
        "metadata": {"source": SOURCE, "fetched_at": datetime.now(timezone.utc).isoformat(), "tile_zoom": TILE_ZOOM},
        "features": features,
    }
    encoded = json.dumps(collection, ensure_ascii=False, separators=(",", ":")).encode()
    checksum = hashlib.sha256(encoded).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".geojson.tmp")
    temporary.write_bytes(encoded)
    temporary.replace(output)
    with db.connect() as conn:
        conn.execute(
            "UPDATE map_sync SET source_url=?,fetched_at=?,checksum=?,feature_count=?,status='ready' WHERE id=1",
            (SOURCE, collection["metadata"]["fetched_at"], checksum, len(features)),
        )
    return {"feature_count": len(features), "checksum": checksum, "fetched_at": collection["metadata"]["fetched_at"]}


if __name__ == "__main__":
    db.initialize()
    print(json.dumps(sync_zones(), ensure_ascii=False, indent=2))
