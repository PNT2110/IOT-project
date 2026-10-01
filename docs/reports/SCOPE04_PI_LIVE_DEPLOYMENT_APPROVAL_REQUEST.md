# SCOPE-04 Pi Live Deployment Approval Request

Status: `OWNER_ACCEPTED — BOUNDED MANUAL SMOKE EXECUTED`  
Implementation evidence: `SCOPE04_IMPLEMENTATION=PC_REPO_IMPLEMENTED`  
The Owner accepted the companion proposal on `2026-09-25`. Execution was
limited to the bounded manual deployment documented in
`SCOPE04_PI_DEPLOYMENT_REPORT.md`; systemd/autostart and external F450 browser
testing remain separate follow-up gates.

## Target and operator fields to complete

```text
TARGET_DEVICE_AND_PHYSICAL_LABEL: <OWNER FILL>
PI_HOSTNAME_OR_LOCAL_CONSOLE_LABEL: <OWNER FILL>
RESPONSIBLE_OPERATOR_AT_PI: <OWNER FILL>
APPROVED_TIME_WINDOW: <OWNER FILL>
APPROVAL_TIMESTAMP: <OWNER FILL>
APPROVED_ACCESS_METHOD: <OWNER FILL — local console or explicitly bounded method>
```

No password, PSK, OTP/TOTP, private key, or saved secret belongs in this
packet.

## Current execution/authorization record

The accepted companion proposal was supplied in the Owner instruction for this
turn and is not stored as a repository file. The non-secret facts available in
the execution evidence are:

```text
OWNER_DECISION=ACCEPT_THIS_PROPOSAL
TARGET_OBSERVED=Raspberry Pi 5 Model B Rev 1.0 / hostname pitan
EXECUTION_TARGET=/home/pitan/scope04-pi-web
EXECUTION_SCOPE=bounded manual SCOPE-04 smoke only
OWNER_TIMESTAMP_IN_REPOSITORY=NOT_RECORDED
```

The `<OWNER FILL>` fields below are retained as the original template and are
not treated as current verified facts. See `SCOPE04_PI_DEPLOYMENT_REPORT.md`
for observed execution evidence.

## Proposed bounded deployment

| Item | Proposed value; owner must confirm |
|---|---|
| Source | `/home/pnt/IOT/pi5/web` and `contracts/v1/SCOPE04_PI_WEB_CONTRACT.md` from the approved repository revision |
| Destination | Pi-local application directory: `<OWNER FILL>` |
| Runtime | Python 3.11+ with approved virtual environment: `<OWNER FILL>` |
| Dependencies | Pinned `pi5/requirements-scope04.lock`; installed in isolated Pi venv: `PASS` |
| Bind | `127.0.0.1:8080` loopback or HTTPS local AP address `192.168.4.1:8443`; never `0.0.0.0`/`::` |
| Port | `8080` loopback smoke / `8443` AP HTTPS smoke |
| Camera | Explicit `/dev/video0`; do not substitute `/dev/video1` |
| Service | A new, owner-reviewed `systemd` unit only if separately approved; current package does not provide or start one |
| Autostart | `NOT_DONE`; optional follow-up pending auth bootstrap decision |
| URL | `http://127.0.0.1:8080/` loopback or `https://192.168.4.1:8443/` local AP smoke |
| Recording/persistence | Disabled; no frame persistence and no telemetry history |
| PC sync/TLS | Not included; no PC↔Pi communication |

## Preflight evidence required before any mutation

- target identity and physical label match the owner record;
- local recovery path is verified for this exact test;
- SCOPE-03 AP remains available and its configuration is not changed;
- current `/dev/video0` identity and read permission are re-verified;
- Python/runtime and dependencies are already present or separately approved;
- destination has a rollback copy or documented restore path;
- requested bind is loopback/local AP only and no public route exists;
- no camera recording, secret storage, or actuator route is enabled.

If any preflight fact differs, stop and request corrected approval.

## Rollback proposal

Stop only the newly approved Pi web unit, restore the prior application files
from the owner-approved rollback location, remove only the new local web
listener/unit, and verify the existing SCOPE-03 AP service is unchanged. No
NetworkManager reset, AP rebuild, reboot, firewall flush, profile deletion,
firmware work, or broad cleanup is authorized by this packet.

## Explicit default prohibitions

```text
NETWORK_CHANGE=NO
PUBLIC_BIND=NO
CAMERA_RECORDING=NO
FRAME_PERSISTENCE=NO
PC_SYNC=NO
FIRMWARE_OR_ESP32_GNSS_WORK=NO
ACTUATOR_OR_ARM_DISARM=NO
SCOPE05_PLUS=NO
```

Required decision: `OWNER_LIVE_DEPLOYMENT_AUTHORIZATION=GRANTED | DENIED | REVISE`.
