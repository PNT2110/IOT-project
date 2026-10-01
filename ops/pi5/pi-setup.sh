#!/usr/bin/env bash
# Runs ON the Pi (ops/deploy-pi.ps1 calls it). Installs the Pi web app as a
# service on port 80 and builds the ESP32 firmware.
#   FLASH=1   also upload the firmware to the ESP32 (remove the propellers first)
#   BUILD_FIRMWARE=0   skip the firmware build
set -euo pipefail
APP=$HOME/iot
DATA=$APP/data
cd "$APP"
mkdir -p "$DATA"

echo "== [1/6] System packages"
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip curl v4l-utils >/dev/null

echo "== [2/6] Python environment"
python3 -m venv "$APP/.venv"
"$APP/.venv/bin/pip" install -q --upgrade pip
"$APP/.venv/bin/pip" install -q -r "$APP/edge/pi5/pi5/requirements-scope04.lock" esptool

echo "== [3/6] Devices"
ESP_DEV=$(ls /dev/serial/by-id/usb-Silicon_Labs_CP210* 2>/dev/null | head -1 || true)
[ -z "$ESP_DEV" ] && ESP_DEV=$(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | head -1 || true)
echo "ESP32: ${ESP_DEV:-not found}"
echo "Camera: $(ls /dev/video0 2>/dev/null || echo 'not found')"
sudo usermod -aG dialout,video,netdev "$USER" || true

if [ "${BUILD_FIRMWARE:-1}" = "1" ]; then
  echo "== [4/6] Firmware build (ESP32 Arduino core 2.0.17)"
  export PATH=$HOME/.local/bin:$PATH
  if ! command -v arduino-cli >/dev/null; then
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=$HOME/.local/bin sh
  fi
  [ -f "$HOME/.arduino15/arduino-cli.yaml" ] || arduino-cli config init >/dev/null
  arduino-cli config add board_manager.additional_urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json >/dev/null 2>&1 || true
  arduino-cli core list | grep -q "esp32:esp32 *2.0.17" || { arduino-cli core update-index; arduino-cli core install esp32:esp32@2.0.17; }
  arduino-cli compile -b esp32:esp32:esp32 --output-dir "$APP/firmware/build" "$APP/firmware/FC_can_bang"
  cp "$APP/firmware/build/FC_can_bang.ino.bin" "$APP/firmware/build/FC_can_bang.bin"
  (cd "$APP/firmware/build" && sha256sum FC_can_bang.bin | tee FC_can_bang.bin.sha256)
  if [ "${FLASH:-0}" = "1" ] && [ -n "$ESP_DEV" ]; then
    echo "-- Uploading to $ESP_DEV (propellers must be off)"
    sudo systemctl stop iot-pi-web.service 2>/dev/null || true
    arduino-cli upload -b esp32:esp32:esp32 -p "$ESP_DEV" --input-dir "$APP/firmware/build" "$APP/firmware/FC_can_bang"
  else
    echo "-- Not flashing (set FLASH=1 to upload)"
  fi
else
  echo "== [4/6] Firmware build skipped"
fi

echo "== [5/6] Environment and default admin"
if [ ! -f "$APP/pi.env" ]; then
  echo "Missing $APP/pi.env (deploy-pi.ps1 copies ops/pi5/pi.env)"; exit 1
fi
chmod 600 "$APP/pi.env"
sed -i 's/\r$//' "$APP/pi.env"
sed -i "s#__HOME__#$HOME#g" "$APP/pi.env"
( set -a; . "$APP/pi.env"; set +a; cd "$APP/edge/pi5" && "$APP/.venv/bin/python" -m pi5.cli seed-default-admin )

echo "== [6/6] Service iot-pi-web on port 80"
sudo tee /etc/systemd/system/iot-pi-web.service >/dev/null <<EOF
[Unit]
Description=F450 PNT PVD Pi web
After=network-online.target
Wants=network-online.target
[Service]
User=$USER
WorkingDirectory=$APP/edge/pi5
Environment=PI_ESP_USB_DEVICE=${ESP_DEV}
EnvironmentFile=$APP/pi.env
AmbientCapabilities=CAP_NET_BIND_SERVICE
ExecStart=$APP/.venv/bin/python -m uvicorn pi5.web.asgi:app --host 0.0.0.0 --port 80
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable iot-pi-web.service >/dev/null
sudo systemctl restart iot-pi-web.service
sleep 4
systemctl --no-pager --lines=12 status iot-pi-web.service || true
curl -fsS http://127.0.0.1/health && echo && echo "Pi web is up" || { echo "health check FAILED"; exit 1; }
