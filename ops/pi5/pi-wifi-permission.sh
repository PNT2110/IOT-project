#!/usr/bin/env bash
# Runs ON the Pi, once, with sudo: lets the Pi web service user scan and join
# Wi-Fi through NetworkManager without a desktop session.
set -euo pipefail
sudo tee /etc/polkit-1/rules.d/50-iot-pi-wifi.rules >/dev/null <<EOF
polkit.addRule(function(action, subject) {
  if (subject.user == "$USER" && (action.id == "org.freedesktop.NetworkManager.network-control" || action.id == "org.freedesktop.NetworkManager.wifi.share.protected" || action.id == "org.freedesktop.NetworkManager.wifi.scan" || action.id == "org.freedesktop.NetworkManager.settings.modify.system" || action.id == "org.freedesktop.NetworkManager.settings.modify.own")) {
    return polkit.Result.YES;
  }
});
EOF
echo "Wi-Fi permission installed for $USER:"
nmcli general permissions | grep -E "network-control|wifi.scan|wifi.share.protected|modify.system"
