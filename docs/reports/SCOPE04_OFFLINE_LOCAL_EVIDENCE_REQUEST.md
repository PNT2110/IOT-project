# SCOPE-04 Bounded Offline-Local Evidence Request

Status: `EXECUTED — SUPERSEDED_BY_SCOPE04_OFFLINE_LOCAL_LIVE_REPORT`

This request exists because the authoritative SCOPE-04 acceptance criterion
requires local web/camera/cache operation with upstream down, while the
current live smoke did not make upstream unavailable. It is not an
authorization to change the Pi network.

## Smallest proposed evidence

Use the already deployed SCOPE-04 foreground/manual runtime and an approved
local recovery path. Make only the minimum bounded upstream-unavailable
condition that does not modify the SCOPE-03 AP/STA profiles, routes, firewall,
or `f450-ap.service`. Then verify, with timestamps:

```text
LOCAL_WEB_REACHABLE=PASS/FAIL
AUTHENTICATED_CAMERA=/dev/video0 PASS/FAIL
LOCAL_MAP_CACHE_READABLE=PASS/FAIL
STALE_PROVENANCE_VISIBLE=PASS/FAIL
MOCK_TELEMETRY_VISIBLE=PASS/FAIL
AP_AND_SCOPE03_SERVICE_UNCHANGED=PASS/FAIL
NO_CAMERA_PERSISTENCE=PASS/FAIL
```

If the minimum condition cannot be created without a network mutation, stop
and ask whether PC/mock evidence is accepted for this criterion. Do not use
the prior SCOPE-03 N4 evidence as a substitute; its protocol deviation and
owner-attested evidence class remain unchanged.

## Owner decision fields

```text
OWNER_DECISION=ACCEPT_PC_MOCK_EVIDENCE | AUTHORIZE_BOUNDED_OFFLINE_SMOKE | REQUIRE_OTHER_EVIDENCE
OWNER_APPROVED_ACCESS_METHOD=<OWNER FILL ONLY IF NEEDED>
OWNER_APPROVED_TIME_WINDOW=<OWNER FILL ONLY IF NEEDED>
```

No credentials, network passwords, PSKs, OTP/TOTP values, private keys or
recovery material belong in this request.
