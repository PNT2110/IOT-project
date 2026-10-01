# SCOPE-00 — API và data contracts

## Envelope

```json
{
  "schema_version": "v1",
  "request_id": "uuid",
  "data": {},
  "error": null,
  "observed_at": "2026-09-22T00:00:00Z"
}
```

Errors use `{code, message_for_user, retryable, details_redacted}`. Do not return stack traces, hashes, OTPs or secrets.

## Contract table

| Contract | Method/path (proposal) | Auth | Idempotency/safety |
|---|---|---|---|
| Public map | `GET /api/v1/public/zones?version=` | none, allowlist only | cacheable; only public visibility. |
| Internal map | `GET/POST/PATCH/DELETE /api/v1/internal/zones` | PC Admin/Owner/Operator policy | mutation audit + `If-Match` version. |
| PC auth | `/api/v1/auth/register`, `/login`, `/mfa/*` | staged | rate limit, CSRF, session rotation. |
| Simulated request | `POST /api/v1/simulated/flight-requests` | authenticated eligible user | `Idempotency-Key`; output cannot command FC. |
| Workflow status | `GET /api/v1/simulated/flight-requests/{id}` | object authorization | status includes `SIMULATED`. |
| Pi sync | `GET /api/v1/pi/v1/map`, `/status` | device identity + TLS | cache with `fetched_at`, `stale_at`. |
| Pi health | Pi local `/api/v1/health/network` | Pi session | separate booleans for three reachability signals. |
| Telemetry | `GET /api/v1/pi/telemetry` or WS/SSE | Pi ADMIN/local policy | seq monotonic; stale marker; read-only. |

## GNSS contract

```json
{
  "fix": "NO_FIX|2D|3D|RTK|UNKNOWN",
  "latitude": null,
  "longitude": null,
  "altitude_m": null,
  "hdop": null,
  "accuracy_m": null,
  "observed_at": null,
  "received_at": "2026-09-22T00:00:00Z",
  "source": "ESP32_READ_ONLY",
  "stale": true,
  "availability": "UNAVAILABLE"
}
```

## Telemetry contract

Required metadata: `device_id`, `seq`, `observed_at`, `received_at`, `source_firmware_version`, `units_version`, `stale_after_ms`. Fields not in verified firmware are null/`UNAVAILABLE`. Roll/Pitch/Yaw units and frame convention must be confirmed before display.

## Versioning

Unknown fields are ignored only when safe; breaking changes increment `/vN` and `schema_version`. Every cross-device request carries `request_id`, timestamp window, nonce/signature or mTLS identity as decided in SCOPE-02/06. No contract contains `arm`, `disarm`, motor output or relay command in this prototype.

## SCOPE-02 resolved contract

The SCOPE-02 implementation resolves the proposals above without changing the v1 envelope. Account status and role are separate: an authenticated `PENDING` session may read its own account only, and backend checks `status == ACTIVE` for internal/workflow access. Account statuses are `PENDING`, `ACTIVE`, `REJECTED`, `SUSPENDED`; valid transitions are `PENDING → ACTIVE|REJECTED`, `ACTIVE → SUSPENDED|REJECTED`, and `SUSPENDED → ACTIVE`. `REJECTED` is terminal in this scope. `OWNER` may change another account broadly; an active `ADMIN` may change only a pending PC `GUEST` to `ACTIVE` with the Owner-granted `ACCOUNT_APPROVE` capability. An `ADMIN` without that grant may inspect the paginated review list/detail; `OPERATOR` may not review accounts. `If-Match` carries the numeric account version and `Idempotency-Key` makes repeated status actions safe. Rejection/suspension revokes current sessions and is audited/history-recorded atomically.

Role elevation requests use `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`, accept only `OPERATOR`/`ADMIN`, require an `Idempotency-Key`, and reject duplicate open requests. The requester can query only their own requests. `OWNER` reviews broadly with `If-Match` and an idempotency key; an active `ADMIN` may review only an active PC `GUEST → ADMIN` request with the Owner-granted `ADMIN_ROLE_APPROVE` capability, and that delegated action is approval-only. No path grants `OWNER` and no requester can review itself. Role is reloaded from the database on each request, so an approved change is effective on the next authorized call.

Simulated workflow fields are deliberately minimal: summary, timezone-aware planned start/end and validated synthetic GeoJSON. The state machine is `DRAFT → SUBMITTED → UNDER_REVIEW → NEEDS_INFORMATION|REJECTED|APPROVED_SIMULATED`, with `NEEDS_INFORMATION → SUBMITTED`. No cancel/expire action was invented. Create and transition actions use idempotency records; edits and transitions use `If-Match`. Each serialized item carries `simulated: true`, `label: "SIMULATED — NOT A FLIGHT PERMIT"` and `source`.

Read-only fake Pi v1 endpoints are `GET /api/v1/pi/v1/map` and `GET /api/v1/pi/v1/status`. They require an active PC session plus the local test identity header `X-Fake-Pi-Client: scope02-test-client`; they return public synthetic map data or object-scoped status only. `offline=true` produces `UNSYNCED`/`stale` status and makes no external call. No write endpoint or cross-domain role grant exists.

## SCOPE-02 policy amendment — capability grants

The former `OWNER_ONLY_REVIEW` rule remains in the historical decision record; the current amendment permits an `ACTIVE` PC `ADMIN` to review only when an `ACTIVE` PC `OWNER` has granted a concrete capability to that specific principal. The grant is not a role, wildcard or delegation channel. It has `grantor_user_id`, `grantee_user_id`, JSON actions, `resource_scope=PC_GUEST`, reason, version, created/revoked timestamps and revocation actor/reason. No expiry duration is invented; a non-revoked grant is effective and revocation is checked from the database on every action.

Allowed actions are `ACCOUNT_APPROVE` and `ADMIN_ROLE_APPROVE`. The account action is limited to `PENDING` target role `GUEST` and transition to `ACTIVE`; it cannot reject/suspend or touch Admin/Owner. The role action is limited to approving an active `GUEST` request for `ADMIN`; it cannot reject, self-review, delegate, grant Owner or mutate Pi identity. Owner grant/revoke mutations use `If-Match` and `Idempotency-Key`, and grant/history/audit plus target mutation are transactional. `GET /api/v1/account-review/capabilities` exists only to make UI affordances reflect effective backend capability; it is not an authorization boundary.

Review list/detail and role-review responses expose `effective_capabilities` with the stable `policy` value `OWNER_OR_GRANTED_ADMIN_SCOPED`, boolean compatibility flags, and per-action `allowed`/`scope` metadata. Role review uses the same policy metadata for both Owner and a granted Admin; an Admin role-review list contains only eligible active `GUEST → ADMIN` requests. The metadata is descriptive and does not replace backend authorization.
