# SCOPE-01 v1 contracts

The API envelope is:

```json
{
  "schema_version": "v1",
  "request_id": "uuid",
  "data": {},
  "error": null,
  "observed_at": "UTC ISO-8601"
}
```

Public zones are returned only from `GET /api/v1/public/zones`. Production does
not seed or publish `TEST_FIXTURE` data; the public list is empty until an
authorized operator creates an approved source and publishes a zone. Internal
CRUD is under `/api/v1/internal/zones`, protected by backend RBAC, optimistic
version checks and audit events. Sources are listed/created through
`/api/v1/internal/zone-sources`; only the Owner can create a source record.
There is no Pi, legal flight permission or actuator contract in this PC scope.

## SCOPE-02 workflow additions

All endpoints retain the `schema_version: "v1"` envelope and UTC timestamps. Internal flight-workflow responses include `authority_contract: "PC_INTERNAL_V1"`, `legal_status: "NOT_A_GOVERNMENT_PERMIT"`, `simulated: true` for backward compatibility, and a non-authoritative `source`. The PC decision is never presented as a government permit or an arm command.

### Account review

`GET /api/v1/account-review/users` and `GET /api/v1/account-review/users/{id}` are available to active `OWNER` and `ADMIN` sessions. `OWNER` may mutate status broadly; an `ADMIN` needs the Owner-granted `ACCOUNT_APPROVE` capability and is limited to `PENDING` PC `GUEST → ACTIVE`. Mutations use `POST /api/v1/account-review/users/{id}/status`, an `If-Match` numeric `version`, and a reason. Valid transitions are `PENDING → ACTIVE|REJECTED`, `ACTIVE → SUSPENDED|REJECTED`, and `SUSPENDED → ACTIVE`. `REJECTED` is terminal in this scope. A reviewer cannot review their own account. Rejecting or suspending revokes all current sessions; no credential or MFA material is returned.

The first bootstrap Owner is deliberately not activated through HTTP. The local CLI procedure requires the exact confirmation phrase, the existing owner password, verified email/MFA and a current TOTP code; it creates a redacted audit/history record with no authenticated HTTP actor. This is an operational bootstrap gate, not normal self-approval.

### Role elevation

`POST /api/v1/role-elevations` is available to active `GUEST` or `OPERATOR` users and accepts only `OPERATOR` or `ADMIN`. An `Idempotency-Key` is required; one open request for the same target role is allowed. `GET /api/v1/role-elevations` returns only the caller's requests. Active `OWNER` reviews with `GET /api/v1/role-elevations/review` and `POST /api/v1/role-elevations/{id}/decision`; an active `ADMIN` may use those review endpoints only with the Owner-granted `ADMIN_ROLE_APPROVE` capability and sees eligible active `GUEST → ADMIN` requests. Review mutations use `If-Match` and `Idempotency-Key`. No workflow grants `OWNER`; a requester cannot review their own request.

### Simulated flight request

`POST /api/v1/flight-requests` creates a `DRAFT` from a summary,
timezone-aware planned start/end, validated GeoJSON and the applicant form
fields (`applicant_full_name`, `license_code`, `vehicle`, optional GPS latitude,
longitude and accuracy). The sensitive form fields are encrypted at rest and
the response exposes only a payload digest plus authorized decrypted details.
It requires `Idempotency-Key`. The state machine is:

```text
DRAFT → SUBMITTED → UNDER_REVIEW → NEEDS_INFORMATION|REJECTED|APPROVED_SIMULATED

The older `/api/v1/simulated/flight-requests` paths remain hidden compatibility
aliases for existing clients; the web UI uses the canonical `/api/v1/flight-requests`
contract. `APPROVED_SIMULATED` means only an internal PC decision and does not
authorize a real-world flight.
NEEDS_INFORMATION → SUBMITTED
```

The owner edits only `DRAFT` or `NEEDS_INFORMATION` with `If-Match`. Submit, review and decision actions require both `If-Match` and `Idempotency-Key`. Reviewers are active `OPERATOR`, `ADMIN` or `OWNER`; a submitter cannot decide its own request. There is no cancel/expire action in this scope.

### History and fake Pi adapter

`GET /api/v1/history/{object_type}/{object_id}` returns redacted, paginated transition history only when object authorization succeeds. `GET /api/v1/audit` is Owner-only and returns redacted audit metadata. Mutation and history records are inserted in the same database transaction.

`GET /api/v1/pi/v1/map` and `GET /api/v1/pi/v1/status` are read-only fake-client endpoints. They require an authenticated active PC session plus `X-Fake-Pi-Client: scope02-test-client`; this value is a test identity, not a production credential. `offline=true` returns `sync_state: "UNSYNCED"`, `stale: true` and no external call. No real Pi connection is made.

## SCOPE-02 policy amendment — Owner-granted Admin capability

The earlier `OWNER_ONLY_REVIEW` policy is historical. The amendment adds `capability_grants`, whose principal is one concrete active PC `ADMIN` and whose grantor is an active PC `OWNER`. A grant has `actions`, `resource_scope`, `reason`, `version`, `created_at`, `revoked_at`, revoker and revoke reason. No expiry is inferred; revocation is explicit and takes effect on the next backend authorization check. Grants are not wildcard permissions and cannot be delegated.

`POST /api/v1/account-review/grants` and `GET /api/v1/account-review/grants` are Owner/authorized-view operations; `POST /api/v1/account-review/grants/{id}/revoke` is Owner-only and uses `If-Match` plus `Idempotency-Key`. Allowed actions are `ACCOUNT_APPROVE` and `ADMIN_ROLE_APPROVE`, with scope `PC_GUEST`. A grant may target only another active PC Admin. `GET /api/v1/account-review/capabilities` exposes the current caller's effective UI capability flags; the backend remains authoritative.

An Admin with `ACCOUNT_APPROVE` may only activate a `PENDING` ordinary PC `GUEST`; it cannot reject, suspend, approve an Admin/Owner, or review itself. An Admin with `ADMIN_ROLE_APPROVE` may only approve an active PC `GUEST`'s request to become `ADMIN`; it cannot reject under this delegated scope, review itself, grant/revoke grants, delegate, or grant `OWNER`. Pending/suspended/rejected actors and Pi `USER/ADMIN` identities never satisfy PC reviewer authorization.

Review list/detail and role-review responses include `effective_capabilities` with `policy: OWNER_OR_GRANTED_ADMIN_SCOPED`, compatibility booleans, and per-action `allowed`/`scope` metadata. The role-review list for a delegated Admin is filtered to eligible active `GUEST → ADMIN` requests; the backend decision endpoint remains authoritative.

## Amendment 2026-10-01 — two-level roles, username login, Pi device channel

This section supersedes the earlier text where they differ.

- Roles: `OWNER` (main account), `ADMIN` (level 1: zones, flight review, account
  review, role changes), `OPERATOR` (level 2: zones and flight review only),
  `GUEST` (registered, waiting for approval). Capability grants were removed.
- `POST /api/v1/account-review/users/{id}/status` takes `role` (`ADMIN` or
  `OPERATOR`) when approving a pending account.
  `POST /api/v1/account-review/users/{id}/role` changes the level of an active
  account. Neither can change the `OWNER` or the caller's own account.
- Registration needs `username` (`^[a-z0-9_.-]{3,32}$`). Login takes
  `identifier` (username or email) and `terms_accepted`. The seeded default
  owner has no email and goes from password straight to TOTP.
- A zone source of type `OPERATOR_DRAWN` is created when the default owner is
  seeded, so staff can save zones without creating a source first.
- Pi devices submit flight requests and read decisions through
  `/api/v1/device/*`: see `DEVICE_FLIGHT_CONTRACT.md`.
