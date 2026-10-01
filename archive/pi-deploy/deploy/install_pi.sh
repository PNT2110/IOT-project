#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR=/home/pi5/iot-drone
DATA_DIR=/var/lib/iot-drone
CONFIG_DIR=/etc/iot-drone
VENV_DIR=/opt/iot-drone/venv

if [[ ! -f "$PROJECT_DIR/backend/requirements.txt" || ! -d "$PROJECT_DIR/frontend/dist" ]]; then
  echo "Thiếu source hoặc frontend/dist tại $PROJECT_DIR" >&2
  exit 1
fi

# Archives copied from Windows can carry non-traversable directory modes.
# Normalize only the public production bundle required by the service.
find "$PROJECT_DIR/frontend/dist" -type d -exec chmod 0755 {} +
find "$PROJECT_DIR/frontend/dist" -type f -exec chmod 0644 {} +

apt-get update
apt-get install -y python3-venv python3-pip caddy curl ca-certificates tar unzip acl ufw

if ! id iot-drone >/dev/null 2>&1; then
  useradd --system --home-dir "$DATA_DIR" --shell /usr/sbin/nologin iot-drone
fi
usermod -a -G dialout iot-drone
# Keep pi5's home private while allowing only the service account to traverse
# to the read-only application source below it.
setfacl -m u:iot-drone:x /home/pi5
install -d -o iot-drone -g iot-drone -m 0750 "$DATA_DIR" "$DATA_DIR/maps" "$DATA_DIR/map-assets"
install -d -o root -g iot-drone -m 0750 "$CONFIG_DIR"
install -d -o root -g root -m 0755 /opt/iot-drone

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/backend/requirements.txt"

if [[ ! -f "$CONFIG_DIR/drone.env" ]]; then
  install -o root -g iot-drone -m 0640 "$PROJECT_DIR/backend/.env.example" "$CONFIG_DIR/drone.env"
fi
install -o root -g root -m 0644 "$PROJECT_DIR/deploy/iot-drone.service" /etc/systemd/system/iot-drone.service
install -o root -g root -m 0644 "$PROJECT_DIR/deploy/Caddyfile" /etc/caddy/Caddyfile

systemctl daemon-reload
systemctl enable iot-drone caddy
systemctl restart iot-drone caddy

# LAN firewall. Keep the Pi's existing SSH and desktop access available only
# inside the same subnet while publishing this application on HTTPS only.
ufw default deny incoming
ufw default allow outgoing
ufw allow from 192.168.1.0/24 to any port 22 proto tcp comment 'SSH LAN'
ufw allow from 192.168.1.0/24 to any port 443 proto tcp comment 'Drone HTTPS LAN'
ufw allow from 192.168.1.0/24 to any port 443 proto udp comment 'Drone HTTP3 LAN'
ufw allow from 192.168.1.0/24 to any port 3389 proto tcp comment 'RDP LAN'
ufw allow from 192.168.1.0/24 to any port 5900 proto tcp comment 'VNC LAN'
ufw allow from 192.168.1.0/24 to any port 5353 proto udp comment 'mDNS LAN'
ufw --force enable
systemctl --no-pager --full status iot-drone
