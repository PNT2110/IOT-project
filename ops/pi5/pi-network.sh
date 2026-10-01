#!/usr/bin/env bash
# Runs ON the Pi. Access point + captive portal for the Pi web app.
#   pi-network.sh inspect    read-only report (default)
#   pi-network.sh captive    send every DNS name asked by AP clients to the Pi,
#                            so phones open the portal automatically
# The access point itself is not recreated here: the Pi already broadcasts it.
# The script refuses to touch an interface that carries the default route.
set -euo pipefail
MODE=${1:-inspect}
AP_ADDR=${AP_ADDR:-192.168.4.1}
CONF=/etc/NetworkManager/dnsmasq-shared.d/iot-captive.conf

report() {
  echo "-- devices"; nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status
  echo "-- active connections"; nmcli -t -f NAME,TYPE,DEVICE connection show --active
  echo "-- wifi modes"; for c in $(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="802-11-wireless"{print $1}'); do
    echo "$c: mode=$(nmcli -g 802-11-wireless.mode connection show "$c") ssid=$(nmcli -g 802-11-wireless.ssid connection show "$c") ipv4=$(nmcli -g ipv4.method connection show "$c") autoconnect=$(nmcli -g connection.autoconnect connection show "$c")"
  done
  echo "-- default route"; ip route show default || true
  echo "-- address $AP_ADDR on"; ip -br addr | grep -F "$AP_ADDR" || echo "(no interface has $AP_ADDR)"
  echo "-- services"; systemctl is-active NetworkManager f450-ap hostapd dnsmasq iot-pi-web 2>&1 | paste -sd' '
  echo "-- captive conf"; [ -f "$CONF" ] && cat "$CONF" || echo "(not installed)"
}

ap_connection() {
  for c in $(nmcli -t -f NAME,TYPE connection show --active | awk -F: '$2=="802-11-wireless"{print $1}'); do
    [ "$(nmcli -g 802-11-wireless.mode connection show "$c")" = "ap" ] && { echo "$c"; return 0; }
  done
  return 1
}

case "$MODE" in
  inspect)
    report
    ;;
  captive)
    AP_CON=$(ap_connection) || { echo "No active access-point connection in NetworkManager; nothing changed."; exit 1; }
    AP_DEV=$(nmcli -g GENERAL.DEVICES connection show "$AP_CON")
    if [ "$(nmcli -g ipv4.method connection show "$AP_CON")" != "shared" ]; then
      echo "AP connection '$AP_CON' is not ipv4.method=shared; captive DNS needs NetworkManager's dnsmasq. Nothing changed."; exit 1
    fi
    if ip route show default | grep -qw "dev $AP_DEV"; then
      echo "Refusing: the default route goes through the AP interface $AP_DEV."; exit 1
    fi
    echo "AP connection: $AP_CON on $AP_DEV"
    sudo mkdir -p "$(dirname "$CONF")"
    printf '# Captive portal: every name resolves to the Pi for AP clients.\naddress=/#/%s\n' "$AP_ADDR" | sudo tee "$CONF" >/dev/null
    # Restart only the AP connection so its dnsmasq picks up the file.
    sudo nmcli connection down "$AP_CON" >/dev/null && sudo nmcli connection up "$AP_CON" >/dev/null
    sleep 3
    report
    ;;
  *)
    echo "usage: $0 inspect|captive"; exit 2
    ;;
esac
