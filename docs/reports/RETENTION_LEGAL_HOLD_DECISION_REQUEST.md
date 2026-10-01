# Retention and Legal-Hold Decision Request

**STATUS: `OWNER_ACCEPTED_LOCAL_ONLY_BOUNDARY — INTEGRATION_BLOCKER`**  
**Scope:** SCOPE-04 local-only storage and any future PC↔Pi/public integration.

## Data categories in the SCOPE-04 boundary

| Category | Local-only preparation treatment | Decision needed before persistence/integration |
|---|---|---|
| Local auth/session/audit metadata | Minimize and redact secrets; no credential material in logs | Audit retention/deletion policy |
| Camera frames/snapshots | Recording off; frame persistence none by default | Whether any persistence is allowed and under what retention/legal hold |
| Map cache | Provenance/stale labels required; no unlicensed source assumption | Cache retention/deletion and source/license policy |
| Mock telemetry | Clearly labeled mock; no PII or actuator meaning | Retention only if fixtures/logs are persisted |
| Logs/session metadata | Redacted, local-only and least privilege | Retention and deletion/legal-hold process |

The authoritative documents leave retention duration and legal hold open and require purpose, role, retention and deletion decisions before storing protected data. They do not require a legal-hold duration to be invented for local-only preparation.

## Owner decision block

```text
NO_PC_PI_PII_EXCHANGE_IN_SCOPE04=yes / correct
LOCAL_ONLY_DATA_RETENTION=<owner decision>
CAMERA_RECORDING_DEFAULT=off / correct
CAMERA_FRAME_PERSISTENCE_DEFAULT=none / correct
MOCK_TELEMETRY_RETENTION=<owner decision>
AUDIT_LOG_RETENTION=<owner decision>
LEGAL_HOLD_OVERRIDE=<owner decision/process>
```

Until decided, no camera recording, frame persistence, PC↔Pi PII/status exchange or public deployment is allowed. This is a hard blocker for integration/public deployment and a preparation constraint for local-only SCOPE-04.

## Recorded owner decision

```text
NO_PC_PI_PII_EXCHANGE_IN_SCOPE04=yes
LOCAL_ONLY_DATA_RETENTION=ephemeral/minimum by default; no protected persistent data unless separately approved
CAMERA_RECORDING_DEFAULT=off
CAMERA_FRAME_PERSISTENCE_DEFAULT=none
MOCK_TELEMETRY_RETENTION=runtime ephemeral; synthetic/non-PII MOCK fixtures only
AUDIT_LOG_RETENTION=local minimum necessary; no secrets/credential material/PII
LEGAL_HOLD_OVERRIDE=not applicable while protected data persistence is disabled; new decision required before protected persistence
```

The owner accepted these local-only defaults through `OWNER_DECISION=ACCEPT_THIS_PROPOSAL`. No statutory duration was invented.
