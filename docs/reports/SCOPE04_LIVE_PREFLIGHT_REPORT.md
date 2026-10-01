# SCOPE-04 Live Preflight Report

Captured: `2026-09-25T21:18:14+07:00` (Asia/Ho_Chi_Minh)

```text
TARGET=Raspberry Pi 5 Model B Rev 1.0
HOSTNAME=pitan
CURRENT_USER=pitan
KERNEL=6.18.50+rpt-rpi-2712
PYTHON=3.13.5
DESTINATION=/home/pitan/scope04-pi-web
DESTINATION_STATE=ABSENT
VENV_SUPPORTED=YES
OPENSSL_PRESENT=YES
V4L2_CTL_PRESENT=YES
```

## Read-only checks

- `/dev/video0`: `uvcvideo`, USB UVC capture, read permission `660
  root:video`, external capture node confirmed.
- `f450-ap.service`: active and enabled.
- `ap0`: `UP 192.168.4.1/24`.
- `wlan0`: connected to `netplan-wlan0-C25B`.
- No listener on intended ports 8080/8443.
- No existing destination directory or unrelated user data conflict.
- `fastapi`, `argon2`, `pyotp`, and `uvicorn` are not installed in the base
  Pi Python; user-space isolated venv install is therefore required and is
  authorized by the accepted proposal.

## Deployment preflight completion

- `/home/pitan/scope04-pi-web` was absent before deployment; an isolated
  directory and pre-deploy manifest were created.
- Python `3.13.5` satisfied the pinned runtime set. The lock installed in the
  venv and `pip check` returned no broken requirements.
- `openssl` was present, so a Pi-local self-signed certificate was created for
  the bounded HTTPS smoke. The private key remained on the Pi with mode `600`;
  it was not copied into reports.
- The deployed v2 archive SHA-256 was verified before extraction:
  `f90f70e7c99bac74e419708f0b09bb582287ba5d37e3af79ae1b93386fd9f04c`.

No network state was changed by preflight. Raw serial/MAC/BSSID and secrets
were not retained.
