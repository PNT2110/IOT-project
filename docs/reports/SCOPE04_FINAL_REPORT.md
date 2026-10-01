# SCOPE-04 Final Report — Repository and Bounded Pi Smoke

This report is the execution snapshot. The reconciled current gate is in
`SCOPE04_FINAL_REPORT_CURRENT.md`; its offline-local gate classification
supersedes the earlier completion summary below.

Captured: `2026-09-25` (Asia/Ho_Chi_Minh)

```text
SCOPE04_IMPLEMENTATION=PC_REPO_IMPLEMENTED
SCOPE04_LIVE_PI=BOUNDED_MANUAL_SMOKE_COMPLETE
SCOPE04_NETWORK_MUTATION=NOT_RUN
SCOPE04_PUBLIC_BIND=NO_WILDCARD; AP_LOCAL_HTTPS_ONLY
SCOPE04_CAMERA_LIVE_CAPTURE=PASS_TRANSIENT_NO_PERSISTENCE
SCOPE04_ACTUATOR_CONTROL=NOT_PRESENT
SCOPE04_PC_FEDERATION=NOT_PRESENT
```

## Gate summary

| Gate | Result |
|---|---|
| Baseline and scope boundary | `VERIFIED_ON_PC` |
| Pi-local auth/session/CSRF/rate limit | `PASS_BOUNDED_SYNTHETIC_LIVE` |
| Camera typed adapter and bounded queue | `PASS_LIVE_TRANSIENT` |
| Map cache provenance/stale/offline | `PASS_LIVE_RUNTIME` |
| Mock telemetry contract | `PASS_LIVE_RUNTIME` |
| 3D safe unavailable behavior | `PASS_LIVE_RUNTIME` |
| Local-only web API/UI shell | `PASS_LOOPBACK_AND_AP_LOCAL_TLS` |
| Regression suite | `47 passed, 1 warning` |
| External F450 browser auth | `NOT_RUN` |
| Systemd unattended deployment | `BLOCKED_AUTH_BOOTSTRAP_DECISION` |
| Resource measurement | `PASS_SHORT_SAMPLE` |

The bounded manual deployment/smoke is complete within the accepted scope.
The next action is a separate decision on persistent local-account bootstrap
and unattended systemd operation, plus optional external F450 browser testing.
No SCOPE-03 network mutation or SCOPE-05+ work is authorized by this report.
