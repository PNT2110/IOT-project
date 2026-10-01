# SCOPE-04 Implementation Report

Status: `REPOSITORY_PHASE=PC_REPO_IMPLEMENTED`  
Live Pi bounded smoke: `LIVE_PI_BOUNDED_SMOKE=EXECUTED`  
Persistent service: `PERSISTENT_SERVICE_DEPLOYMENT=NOT_DONE`  
External browser: `EXTERNAL_BROWSER_VALIDATION=NOT_RUN`

## Delivered

- `pi5/web/models.py`: typed camera, cache, telemetry, role, and response
  envelope models.
- `pi5/web/auth.py`: isolated Pi-local USER/ADMIN auth/session service with
  password hashing, ephemeral MFA challenge, secure session material,
  CSRF-token validation, expiration, rate limiting, and redacted audit
  events.
- `pi5/web/camera.py`: mock adapter and explicit V4L2 probe with bounded frame
  queue, typed unavailable/busy/permission/format/open/read failures, safe
  consumer disconnect, and `/dev/video1` guard.
- `pi5/web/cache.py`: offline-only map cache with source, source type, fetch or
  generation time, cache version, stale-after, license, and stale state.
- `pi5/web/telemetry.py`: versioned mock telemetry and deterministic 3D view
  model with no invented orientation.
- `pi5/web/app.py`: local-only FastAPI app factory, authenticated read-only
  routes, one-frame bounded local camera response, secure cookies,
  CSRF-protected logout, and a small labeled local UI.
- `contracts/v1/SCOPE04_PI_WEB_CONTRACT.md`: versioned route and invariant
  contract.

No runtime is bound or started by importing this package. `0.0.0.0`, `::`, and
empty bind hosts are rejected.

## Live deployment addendum

The accepted bounded cycle deployed the runtime to `/home/pitan/scope04-pi-web`
with the pinned venv and exercised loopback plus local HTTPS on
`192.168.4.1:8443`. The deployed entrypoint now selects the explicit
`/dev/video0` V4L2 adapter and reads at most one transient bounded frame per
request. No systemd unit was installed because the current Pi-local auth store
is ephemeral and no persistent account/bootstrap decision was approved.
