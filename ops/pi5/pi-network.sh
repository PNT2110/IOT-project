#!/usr/bin/env bash
# Runs ON the Pi. Access point + captive portal on the same radio as the
# Wi-Fi client (wlan0 = client, ap0 = access point).
#   pi-network.sh inspect    read-only report (default)
#   pi-network.sh install    needs sudo: always-on access point, channel
#                            follow-up when the client joins a network, and
#                            captive-portal DNS
# Only wlan0/ap0 are touched; the wired interface is left alone.
set -euo pipefail
MODE=${1:-inspect}
STA=${STA:-wlan0}
AP=${AP:-ap0}
PROFILE=${PROFILE:-F450-1RADIO}
AP_SSID=${AP_SSID:-F450}
AP_ADDR=${AP_ADDR:-192.168.4.1}
CAPTIVE=/etc/NetworkManager/dnsmasq-shared.d/iot-captive.conf

report() {
  echo "-- devices"; nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status
  echo "-- default route"; ip route show default || true
  echo "-- radio"; iw dev 2>/dev/null | grep -E "Interface|type|channel|ssid" || true
  echo "-- $AP_ADDR on"; ip -br addr | grep -F "$AP_ADDR" || echo "(no interface has $AP_ADDR)"
  echo "-- services"; systemctl is-active NetworkManager f450-ap iot-pi-web 2>&1 | paste -sd' '
  echo "-- captive conf"; [ -f "$CAPTIVE" ] && cat "$CAPTIVE" || echo "(not installed)"
}

install_ap() {
  if ! nmcli -t -f NAME connection show | grep -qx "$PROFILE"; then
    echo "Creating access-point profile $PROFILE (SSID $AP_SSID)"
    read -r -s -p "New Wi-Fi password for $AP_SSID (8-63 characters): " AP_PSK; echo
    [ "${#AP_PSK}" -ge 8 ] && [ "${#AP_PSK}" -le 63 ] || { echo "Password length is invalid."; exit 1; }
    sudo nmcli connection add type wifi ifname "$AP" con-name "$PROFILE" autoconnect no ssid "$AP_SSID" \
      802-11-wireless.mode ap 802-11-wireless.band bg 802-11-wireless.channel 6 \
      ipv4.method shared ipv4.addresses "$AP_ADDR/24" ipv6.method disabled \
      wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$AP_PSK" >/dev/null
    unset AP_PSK
  fi

  # The access point must come up whether or not the client is connected, and
  # must sit on the client's channel because both share one radio.
  sudo tee /usr/local/sbin/f450-ap.sh >/dev/null <<EOF
#!/bin/bash
# F450 access point on the same radio as the Wi-Fi client. Installed by ops/pi5/pi-network.sh.
STA="$STA"; AP="$AP"; PROFILE="$PROFILE"; DEFAULT_CHANNEL=6
exec 9>/run/f450-ap.lock
flock -w 60 9 || exit 1

ensure_iface() {
  if ! iw dev | grep -q "Interface \$AP"; then
    iw dev "\$STA" interface add "\$AP" type __ap || return 1
  fi
  ip link set "\$AP" up || true
  nmcli device set "\$AP" managed yes || true
  for _ in \$(seq 1 20); do
    nmcli -g GENERAL.STATE device show "\$AP" 2>/dev/null | grep -qE "disconnected|connected" && return 0
    sleep 1
  done
  return 1
}

start_ap() {
  ensure_iface || { echo "[F450] \$AP is not ready"; exit 1; }
  channel=""
  if iw dev "\$STA" link | grep -q "^Connected"; then
    channel="\$(iw dev "\$STA" info | awk '/channel/ {print \$2; exit}')"
  fi
  [ -n "\$channel" ] || channel="\$DEFAULT_CHANNEL"
  band=bg; [ "\$channel" -gt 14 ] && band=a
  current="\$(nmcli -g 802-11-wireless.channel connection show "\$PROFILE")"
  active="\$(nmcli -g GENERAL.CONNECTION device show "\$AP" 2>/dev/null)"
  if [ "\$current" = "\$channel" ] && [ "\$active" = "\$PROFILE" ]; then
    echo "[F450] access point already up on channel \$channel"; exit 0
  fi
  nmcli connection modify "\$PROFILE" 802-11-wireless.band "\$band" 802-11-wireless.channel "\$channel"
  nmcli connection down "\$PROFILE" 2>/dev/null || true
  nmcli connection up "\$PROFILE" ifname "\$AP" && echo "[F450] access point up on channel \$channel"
}

case "\$1" in
  start) start_ap ;;
  stop) nmcli connection down "\$PROFILE" 2>/dev/null || true ;;
  *) echo "usage: \$0 start|stop"; exit 2 ;;
esac
EOF
  sudo chmod 755 /usr/local/sbin/f450-ap.sh

  sudo tee /etc/systemd/system/f450-ap.service >/dev/null <<EOF
[Unit]
Description=F450 Wi-Fi access point (always on, same radio as the client)
After=NetworkManager.service
Wants=NetworkManager.service
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/f450-ap.sh start
ExecStop=/usr/local/sbin/f450-ap.sh stop
TimeoutStartSec=120
[Install]
WantedBy=multi-user.target
EOF

  # When the client joins or leaves a network the radio changes channel:
  # bring the access point back on the new channel.
  sudo tee /etc/NetworkManager/dispatcher.d/90-f450-ap >/dev/null <<EOF
#!/bin/bash
[ "\$1" = "$STA" ] || exit 0
case "\$2" in
  up|down) (sleep 3; /usr/local/sbin/f450-ap.sh start) >/dev/null 2>&1 & ;;
esac
EOF
  sudo chmod 755 /etc/NetworkManager/dispatcher.d/90-f450-ap

  sudo mkdir -p "$(dirname "$CAPTIVE")"
  printf '# Captive portal: every name resolves to the Pi for access-point clients.\naddress=/#/%s\n' "$AP_ADDR" | sudo tee "$CAPTIVE" >/dev/null

  sudo systemctl daemon-reload
  sudo systemctl enable f450-ap.service >/dev/null
  sudo systemctl restart f450-ap.service || true
  sleep 4
  report
}

case "$MODE" in
  inspect) report ;;
  install) install_ap ;;
  *) echo "usage: $0 inspect|install"; exit 2 ;;
esac
