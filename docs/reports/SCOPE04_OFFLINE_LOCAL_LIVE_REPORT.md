# SCOPE-04 Offline-Local Live Report

Evidence class: `VERIFIED_ON_PI_PROGRAMMATIC_OBSERVER`  
Target: `pitan` / Raspberry Pi 5 Model B Rev 1.0  
Observer timestamp during upstream-down state: `2026-09-25T18:49:57Z`
(`2026-09-26T01:49:57+07:00`).

The bounded cycle used a transient user-systemd recovery timer with a 90-second
deadline. The only authorized failure action was:
`sudo nmcli connection down id netplan-wlan0-C25B`. Recovery restored the same
profile with `nmcli connection up ... ifname wlan0`; no AP profile, route,
firewall, reboot, or NetworkManager profile mutation was performed.

| Check | Before | Upstream down | After recovery | Evidence class | Result |
|---|---|---|---|---|---|
| `wlan0` upstream | connected / `netplan-wlan0-C25B` | `disconnected` | connected / same profile | PI observer + post-check | `PASS` |
| `ap0` / F450 | `192.168.4.1/24` | present / same address | present / same address | PI observer + post-check | `PASS` |
| `f450-ap.service` | active/enabled | active | active/enabled | PI observer + post-check | `PASS` |
| Local HTTPS web | listener `192.168.4.1:8443` | health response successful | stopped during cleanup | PI observer | `PASS` |
| Pi-local auth | synthetic USER session | authenticated `/auth/me` successful | not applicable after cleanup | PI observer | `PASS` |
| `/dev/video0` camera | verified | authenticated `200 image/jpeg`, transient only | permissions unchanged | PI observer + post-check | `PASS` |
| Local map cache | stale synthetic fixture | payload/provenance readable, `STALE` visible | not applicable after cleanup | PI observer | `PASS` |
| `MOCK` telemetry | source `MOCK` | source `MOCK`, missing values `null`/unavailable | not applicable after cleanup | PI observer | `PASS` |
| 3D safe unavailable state | disabled without orientation | `UNAVAILABLE`, animation false | not applicable after cleanup | PI observer | `PASS` |
| No control route | `404` | `404` | not applicable after cleanup | PI observer | `PASS` |
| No PC-sync route | `404` | `404` | not applicable after cleanup | PI observer | `PASS` |

## Recovery and cleanup

```text
TRANSIENT_RECOVERY_ARMED=PASS
TRANSIENT_RECOVERY_TIMER=90_seconds
STA_RECONNECTED=PASS
AP_ADDRESS_192.168.4.1_PRESENT=PASS
F450_AP_SERVICE_ACTIVE_AFTER_RECOVERY=PASS
NO_8443_LISTENER_AFTER_CLEANUP=PASS
TRANSIENT_RECOVERY_JOB_REMOVED_OR_EXPIRED=PASS
NO_SCOPE04_PERSISTENT_SYSTEMD_UNIT=PASS
NETWORKMANAGER_PROFILES_UNMODIFIED=PASS
CAMERA_PERMISSIONS_UNCHANGED=PASS
NO_CAMERA_PERSISTENCE=PASS
```

No raw camera frame, password, PSK, OTP/TOTP, private key, raw client
identifier or secret was stored in this report.
