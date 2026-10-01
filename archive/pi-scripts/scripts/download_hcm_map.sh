#!/usr/bin/env bash
set -euo pipefail

DATA_DIR=$(readlink -m "${DRONE_DATA_DIR:-/var/lib/iot-drone}")
if [[ -z "$DATA_DIR" || "$DATA_DIR" == "/" ]]; then
  echo "DRONE_DATA_DIR không an toàn" >&2
  exit 1
fi
MAP_DIR="$DATA_DIR/maps"
ASSET_DIR="$DATA_DIR/map-assets"
MAX_BYTES=6442450944
MIN_FREE_KB=8388608
WORK_DIR=$(mktemp -d /tmp/iot-drone-map.XXXXXX)
if [[ "$WORK_DIR" != /tmp/iot-drone-map.* ]]; then
  echo "Thư mục tạm không hợp lệ" >&2
  exit 1
fi
trap 'rm -rf -- "$WORK_DIR"' EXIT

free_kb=$(df --output=avail -k "$DATA_DIR" | tail -1 | tr -d ' ')
if (( free_kb < MIN_FREE_KB )); then
  echo "Cần giữ tối thiểu 8 GB trống trước khi tải map" >&2
  exit 1
fi

if ! command -v pmtiles >/dev/null 2>&1; then
  asset_url=$(python3 - <<'PY'
import json, urllib.request
request = urllib.request.Request('https://api.github.com/repos/protomaps/go-pmtiles/releases/latest', headers={'User-Agent':'IOT-Drone-Station/0.1'})
release = json.load(urllib.request.urlopen(request))
for asset in release['assets']:
    if asset['name'].endswith('_Linux_arm64.tar.gz'):
        print(asset['browser_download_url'])
        break
else:
    raise SystemExit('Không tìm thấy pmtiles Linux arm64')
PY
)
  curl --fail --location --retry 3 "$asset_url" -o "$WORK_DIR/pmtiles.tar.gz"
  tar -xzf "$WORK_DIR/pmtiles.tar.gz" -C "$WORK_DIR"
  install -m 0755 "$WORK_DIR/pmtiles" /usr/local/bin/pmtiles
fi

source_url=$(python3 - <<'PY'
import json, urllib.request
request = urllib.request.Request('https://build-metadata.protomaps.dev/builds.json', headers={'User-Agent':'IOT-Drone-Station/0.1'})
builds = sorted(json.load(urllib.request.urlopen(request)), key=lambda item: item['key'], reverse=True)
print('https://build.protomaps.com/' + builds[0]['key'])
PY
)

mkdir -p "$MAP_DIR" "$ASSET_DIR"

build_map() {
  local zoom=$1
  rm -f -- "$WORK_DIR/mainland.pmtiles" "$WORK_DIR/condao.pmtiles" "$WORK_DIR/hcm.pmtiles"
  pmtiles extract "$source_url" "$WORK_DIR/mainland.pmtiles" --bbox=106.30,10.30,107.65,11.65 --maxzoom="$zoom"
  # Mainland already contains the shared world/low-zoom tiles. Starting the
  # island extract at z9 keeps both archives disjoint so `pmtiles merge` can
  # combine them without duplicating z0..z8.
  pmtiles extract "$source_url" "$WORK_DIR/condao.pmtiles" --bbox=106.45,8.55,106.85,8.85 --minzoom=9 --maxzoom="$zoom"
  pmtiles merge "$WORK_DIR/mainland.pmtiles" "$WORK_DIR/condao.pmtiles" "$WORK_DIR/hcm.pmtiles"
  pmtiles verify "$WORK_DIR/hcm.pmtiles"
}

build_map 15
map_size=$(stat -c '%s' "$WORK_DIR/hcm.pmtiles")
if (( map_size > MAX_BYTES )); then
  build_map 14
  map_size=$(stat -c '%s' "$WORK_DIR/hcm.pmtiles")
fi
if (( map_size > MAX_BYTES )); then
  echo "Map vẫn vượt 6 GB sau khi giảm xuống zoom 14" >&2
  exit 1
fi

install -o iot-drone -g iot-drone -m 0640 "$WORK_DIR/hcm.pmtiles" "$MAP_DIR/hcm.pmtiles.new"
mv -f -- "$MAP_DIR/hcm.pmtiles.new" "$MAP_DIR/hcm.pmtiles"

curl --fail --location --retry 3 https://codeload.github.com/protomaps/basemaps-assets/zip/refs/heads/main -o "$WORK_DIR/assets.zip"
unzip -q "$WORK_DIR/assets.zip" -d "$WORK_DIR/assets"
rm -rf -- "$ASSET_DIR/fonts" "$ASSET_DIR/sprites"
cp -a "$WORK_DIR/assets/basemaps-assets-main/fonts" "$ASSET_DIR/fonts"
cp -a "$WORK_DIR/assets/basemaps-assets-main/sprites" "$ASSET_DIR/sprites"
chown -R iot-drone:iot-drone "$ASSET_DIR"

echo "Map TPHCM đã sẵn sàng: $MAP_DIR/hcm.pmtiles ($map_size bytes)"
