# SCOPE-04 Live Evidence Reconciliation

Captured: `2026-09-25` (Asia/Ho_Chi_Minh)

## Canonical status vocabulary

```text
REPOSITORY_PHASE=PC_REPO_IMPLEMENTED
LIVE_PI_BOUNDED_SMOKE=EXECUTED
PERSISTENT_SERVICE_DEPLOYMENT=NOT_DONE
EXTERNAL_BROWSER_VALIDATION=NOT_RUN
LIVE_HTTPS_LISTENER=192.168.4.1:8443 (foreground smoke; stopped after cleanup)
OFFLINE_LOCAL_GATE=PASS_LIVE
```

The earlier implementation header value `SCOPE04_LIVE_PI=NOT_RUN` was stale;
the bounded live addendum and deployment report are later evidence. It is now
replaced by the explicit distinctions above. No historical evidence was
erased.

## Authorization reconciliation

The accepted companion Owner proposal was supplied in the Owner instruction,
not as a repository file. The repository approval request still contains its
original `<OWNER FILL>` template fields. The current execution record therefore
uses only observed facts: target `pitan` / Raspberry Pi 5 Model B Rev 1.0,
destination `/home/pitan/scope04-pi-web`, and `OWNER_DECISION=ACCEPT_THIS_PROPOSAL`.
The Owner timestamp was not recorded in the repository and is not invented.

## Evidence preserved

- Pi runtime installed from the pinned lock in an isolated venv; `pip check`
  passed.
- Loopback health/local shell smoke passed.
- Foreground HTTPS listener was exactly `192.168.4.1:8443`; secure-cookie
  authentication and protected camera request passed with synthetic users.
- `/dev/video0` returned one transient bounded JPEG frame; no file was written.
- Cache provenance/stale label, `MOCK` telemetry, `UNAVAILABLE` values and
  disabled 3D behavior were observed at runtime.
- No wildcard listener, control route, PC-sync route, firmware route, network
  mutation, camera persistence, or SCOPE-03 change was observed.
- External F450 browser validation was not run. Systemd/autostart was not
  installed; both remain optional/deferred.

## Evidence limits

The authoritative upstream-down criterion is now supported by the bounded
observer: `wlan0` was disconnected while AP/local HTTPS/auth/camera/cache/
telemetry/3D remained usable, then the same STA profile recovered. SCOPE-03
N4 was not rerun or promoted.
