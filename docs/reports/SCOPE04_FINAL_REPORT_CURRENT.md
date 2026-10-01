# SCOPE-04 Current Final Gate Report

Current status: `SCOPE04=PASS`

```text
REPOSITORY_PHASE=PC_REPO_IMPLEMENTED
LIVE_PI_BOUNDED_SMOKE=EXECUTED
PERSISTENT_SERVICE_DEPLOYMENT=NOT_DONE
EXTERNAL_BROWSER_VALIDATION=NOT_RUN
OFFLINE_LOCAL_GATE=PASS_LIVE
SCOPE05=BLOCKED_NOT_OPENED
SCOPE04_OWNER_DECISION=ACCEPT
```

The bounded live deployment, final upstream-down observer and explicit Owner
acceptance close the documented SCOPE-04 hard gates. This is a bounded local
prototype acceptance, not a claim of production deployment, endurance,
external-browser validation or later-scope integration readiness.

## Completed SCOPE-04 requirements

- Pi-local authenticated web boundary and role/CSRF/rate-limit behavior.
- Read-only camera adapter with typed failures and transient authenticated
  camera evidence from `/dev/video0`.
- Provenance-labelled stale map cache and explicitly labelled MOCK telemetry.
- Missing-fix and missing-orientation behavior represented as unavailable;
  no invented telemetry or actuator/control route.
- Upstream-down local observer: `wlan0` disconnected while `ap0`, F450,
  local HTTPS/auth, camera, cache, MOCK telemetry and safe 3D state remained
  usable; the same STA profile recovered.
- Security, resource and documentation gates supported by the recorded PC and
  bounded Pi evidence.

## Optional operational hardening

- External physical-browser validation.
- Persistent systemd/autostart deployment.
- Persistent account/auth store and production certificate trust.

## Deferred later-scope requirements

- PC↔Pi TLS/device identity and protected persistence/retention/legal hold.
- Real ESP32/GNSS telemetry and any SCOPE-05+ hardware work.
- ARM/DISARM, actuator, flight-control, firmware or public deployment claims.

## Gate matrix

| Gate | Authoritative requirement | Evidence | Class | Result | Remaining gap |
|---|---|---|---|---|---|
| `AUTH_GATE` | Pi-local auth/MFA, USER/ADMIN, authenticated local stream, CSRF/rate limit | PC tests plus HTTPS Pi synthetic USER/ADMIN smoke | PC mock + PI runtime programmatic | `PASS` | No external browser claim |
| `CAMERA_GATE` | Read-only adapter, typed errors, authenticated local stream, bounded/no persistence | `/dev/video0` probe, transient JPEG, authenticated request, disconnect, `/dev/video99` typed error | PI runtime | `PASS` | No sustained FPS/endurance claim |
| `CACHE_GATE` | Local cache provenance and visible stale state | Live stale synthetic fixture plus PC unavailable/stale tests | PC mock + PI runtime | `PASS` | No legal validity claim |
| `MOCK_TELEMETRY_GATE` | Versioned mock source, unknown values unavailable, no-fix/stale semantics | Live `MOCK/UNAVAILABLE`; PC explicit `NO_FIX/STALE` test | PC mock + PI runtime | `PASS` | No ESP32/GNSS access |
| `3D_GATE` | Use only present orientation; missing orientation safe | Live disabled `UNAVAILABLE`; PC present-orientation test | PC mock + PI runtime | `PASS` | No hardware orientation |
| `OFFLINE_LOCAL_GATE` | Local web/camera/cache work with upstream down | Observer saw `wlan0` disconnected while local HTTPS/auth/camera/cache remained usable; STA recovered | PI runtime observer | `PASS` | No sustained/endurance claim |
| `AP_TRANSPORT_GATE` | Authenticated local web with safe local transport | HTTPS `192.168.4.1:8443`, secure cookie, no wildcard | PI runtime | `PASS` | External browser separate |
| `EXTERNAL_BROWSER_GATE` | Not stated as SCOPE-04 hard DoD | No real F450 browser run | Operational follow-up | `NOT_REQUIRED` | Optional client validation |
| `SECURITY_GATE` | No actuator/control path, no persistence/public exposure, redacted logs | Route/listener/runtime checks | PC + PI smoke | `PASS` | Later hardening remains deferred |
| `RESOURCE_GATE` | Resource tests/measurements with no invented thresholds | Short Pi RSS/CPU/FD/load sample | PI short smoke | `PASS` | Not capacity/endurance evidence |
| `DOCUMENTATION_GATE` | Reports, evidence and owner approval before SCOPE-06 | Current reports plus this reconciliation and owner packet | Repository | `PASS` | No SCOPE-04 hard-gate gap |

## Classification of commonly confused items

| Item | Classification | Reason |
|---|---|---|
| systemd/autostart | `OPTIONAL_OPERATIONAL_HARDENING` | Not required by SCOPE-04 DoD text |
| persistent account DB | `OPTIONAL_OPERATIONAL_HARDENING` | Current scope explicitly uses local/ephemeral prototype boundaries; persistence needs bootstrap/retention decision |
| external physical browser | `OPTIONAL_OPERATIONAL_HARDENING` | Authoritative scope requires local web, not a named external-browser gate |
| production certificate trust | `DEFERRED_PRODUCTION_HARDENING` | Local HTTPS smoke passed without modifying trust stores |
| PC↔Pi TLS/device identity | `BLOCKS_ONLY_LATER_SCOPE` | Needed for future integration, not local-only SCOPE-04 completion |
| retention/legal hold | `BLOCKS_ONLY_LATER_SCOPE` | No protected persistence was enabled |

All documented hard SCOPE-04 gates are now supported by the recorded evidence.
Owner acceptance is still required; it is not pre-filled by Codex.
