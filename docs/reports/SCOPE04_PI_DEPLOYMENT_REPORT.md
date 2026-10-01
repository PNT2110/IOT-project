# SCOPE-04 Pi Deployment Report

Status: `DEPLOYMENT=COMPLETED_BOUNDED_MANUAL_SMOKE`  
Target: `pitan` / Raspberry Pi 5 Model B Rev 1.0  
Deployment window: `2026-09-25` (Asia/Ho_Chi_Minh)

## Authorization used

`OWNER_DECISION=ACCEPT_THIS_PROPOSAL` was supplied for the companion
SCOPE-04 deployment proposal. Scope was limited to one Pi-local SCOPE-04
deployment/smoke cycle. No SCOPE-03 mutation, N4 rerun, or SCOPE-05+ work was
performed.

## Deployment

- Source: approved `pi5/web`, SCOPE-04 contract, and pinned lock artifact.
- Destination: `/home/pitan/scope04-pi-web`.
- Pre-deploy state: destination absent; manifest recorded before writing.
- Runtime: Python `3.13.5`, isolated `.venv`, `pip check` clean.
- Dependencies: pinned lock installed in user-owned venv; no `sudo`, apt,
  global pip, driver, kernel, or OS change.
- Camera: `/dev/video0`; `/dev/video1` was not substituted.
- Transport: Pi-local HTTPS test certificate, AP address `192.168.4.1:8443`.
  Key stayed on Pi with mode `600`; no system trust store changed.
- Foreground/manual smoke passed on loopback `127.0.0.1:8080` and on the
  bounded HTTPS AP address.
- `systemd` was not created/enabled. The current auth service is in-memory and
  no persistent local-account bootstrap or production secret provisioning was
  approved; unattended autostart would otherwise produce an unprovisioned
  auth surface. This is reported as a follow-up gate, not hidden.

## Rollback state

The pre-deploy manifest records that the destination was absent. The original
SCOPE-04 deployment archives remain on the Pi for bounded rollback/reference;
no unrelated Pi files were touched.
