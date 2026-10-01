# SCOPE-02 Owner Acceptance Packet — Current

**STATUS: `OWNER_ACCEPTED — 2026-09-24`**  
**Purpose:** One concise decision block for the already implemented/tested PC amendment. No source change is requested by this packet.

## Decisions to accept or correct

### A. Capability matrix

`OWNER` may grant/revoke concrete `ACCOUNT_APPROVE` and/or `ADMIN_ROLE_APPROVE` capabilities to another active PC `ADMIN`, scoped to `PC_GUEST`. A granted Admin may only approve pending `PC.GUEST → ACTIVE` or active `PC.GUEST → ADMIN` as applicable. No grant fails closed; no Admin→Owner, self-review, redelegation or Pi federation.

### B. PC.GUEST mapping

The amended policy treats the eligible PC account target as `PC.GUEST`; it does not invent a PC `USER` role and does not alter the separate Pi `USER/ADMIN` domain.

### C. Additive migration

Accept or correct migration `a71e8c4b2d90_owner_admin_capability_grants`, including its tested upgrade/downgrade/restore behavior.

### D. Local-only bootstrap procedure

Accept or correct the existing local CLI bootstrap Owner procedure requiring explicit confirmation, password and current TOTP, with no HTTP self-activation.

### E. Effective response contract

Accept or correct `OWNER_OR_GRANTED_ADMIN_SCOPED` plus per-action effective scope metadata in API/UI responses.

## One-block owner response

```text
SCOPE02_AMENDMENT_OWNER_DECISION=ACCEPT / CORRECT
CAPABILITY_MATRIX=ACCEPT / CORRECT
PC_GUEST_MAPPING=ACCEPT / CORRECT
MIGRATION_A71E8C4B2D90=ACCEPT / CORRECT
LOCAL_BOOTSTRAP=ACCEPT / CORRECT
EFFECTIVE_RESPONSE_CONTRACT=ACCEPT / CORRECT
```

The packet was pending until the owner returned the explicit decision below.

## Recorded owner decision

The owner explicitly returned `OWNER_DECISION=ACCEPT_THIS_PROPOSAL`, which accepts decisions A–E above. This records owner acceptance of the amendment packet; it does not alter historical test reports or create a Pi/PC integration permission.

```text
SCOPE02_AMENDMENT_OWNER_DECISION=ACCEPT
CAPABILITY_MATRIX=ACCEPT
PC_GUEST_MAPPING=ACCEPT
MIGRATION_A71E8C4B2D90=ACCEPT
LOCAL_BOOTSTRAP=ACCEPT
EFFECTIVE_RESPONSE_CONTRACT=ACCEPT
```
