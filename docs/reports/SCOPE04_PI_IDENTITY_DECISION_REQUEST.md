# SCOPE-04 Pi-Local Identity Decision Request

**STATUS: `OWNER_ACCEPTED — 2026-09-24`**  
**Scope:** Local SCOPE-04 Pi Web only; no PC↔Pi integration authorization.

## Proposed narrow policy

```text
PI_LOCAL_IDENTITY_POLICY:
- Pi-local accounts and sessions only.
- Pi-local USER and ADMIN roles remain separate from PC roles.
- Pi.ADMIN cannot become PC.Owner and cannot grant PC authority.
- No identity federation or implicit account linking.
- No PC credential reuse on Pi by assumption.
- No PC↔Pi PII/status sync in SCOPE-04.
- Device identity/TLS for real PC↔Pi communication is deferred to the first scope that requires that communication.
```

This matches the current authentication/security documents: PC and Pi identity domains are independent, Pi ADMIN is local-only, and future federation requires a separate ADR/threat model. SCOPE-04 may use authenticated local web sessions only if the owner accepts this boundary.

## Owner decision

```text
PI_LOCAL_IDENTITY_POLICY=ACCEPT / CORRECT
PC_PI_FEDERATION_IN_SCOPE04=NO
PC_PI_PII_STATUS_SYNC_IN_SCOPE04=NO
DEVICE_IDENTITY_TLS_DEFERRED_UNTIL_PC_PI_COMMUNICATION=ACCEPT / CORRECT
```

No identity linkage or cross-device exchange is implemented by this request.

## Recorded owner decision

```text
PI_LOCAL_IDENTITY_POLICY=ACCEPTED
PC_PI_FEDERATION_IN_SCOPE04=NO
PC_PI_PII_STATUS_SYNC_IN_SCOPE04=NO
DEVICE_IDENTITY_TLS_DEFERRED_UNTIL_PC_PI_COMMUNICATION=ACCEPTED
```
