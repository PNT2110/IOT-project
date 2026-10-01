# Publishing a firmware release

The Pi's Firmware tab reads the latest release of the GitHub repository named
in `PI_FW_GITHUB_REPO` (`owner/repo`) and expects two assets:

- `FC_can_bang.bin` — the application image (flashed at `0x10000`)
- `FC_can_bang.bin.sha256` — its SHA-256, in `sha256sum` format

## Build

`ops/deploy-pi.ps1` builds both files on the Pi at `~/iot/firmware/build/`
with Arduino core `esp32:esp32@2.0.17`. To build by hand on the Pi:

```bash
arduino-cli compile -b esp32:esp32:esp32 --output-dir ~/iot/firmware/build ~/iot/firmware/FC_can_bang
```

```bash
cd ~/iot/firmware/build && cp FC_can_bang.ino.bin FC_can_bang.bin && sha256sum FC_can_bang.bin > FC_can_bang.bin.sha256
```

## Publish

Copy the two files to the PC, then on GitHub: repository → Releases → Draft a
new release → choose a tag such as `v1.0.0` → attach both files → Publish.
The tag is the version shown on the Pi.

## What the Pi does

1. Reads the latest release and the published checksum.
2. Downloads the image (4 MB limit) and compares its SHA-256.
3. Refuses if the drone is ARMED or the checksum differs.
4. Pauses the ESP32 serial link, runs `esptool write_flash 0x10000`, resumes.

Remove the propellers before flashing. After a new firmware boots, the ESP32
is BLOCKED until the Pi grants a flight permission again.
