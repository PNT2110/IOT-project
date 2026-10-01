# Project requirements audit — 2026-09-30

This is a source-and-runtime audit against the requested PC public portal, Pi 5
edge web, ESP32 flight-controller/GPS integration and deployment scope. It is
not a claim that the complete hardware system is finished.

## Executive result

`NOT COMPLETE`. The PC foundation is running publicly as a controlled
simulation/prototype and its current security, auth, map and local workflow
are test-covered. The Pi 5, ESP32/GPS, real authority exchange, firmware
update and hardware arm path are intentionally not implemented in the active
source tree.

## Module partition actually present

| Cluster | Active location | Audit result |
|---|---|---|
| PC Server | `server/app/` | FastAPI, SQLite/Alembic, auth/MFA, RBAC, zones, encrypted simulated workflow, audit, security headers/rate limits |
| PC Web | `frontend/src/` | React/Vite public shell, interactive map, auth/MFA panel and authenticated operations workspace |
| Shared contracts | `contracts/v1/` | PC API/data contract and explicit simulation boundary; device schemas still incomplete |
| Tests | `tests/` | PC scope tests plus mock-only Pi edge auth/camera/read-only tests; no hardware tests |
| Pi 5 | `edge/pi5/` | Active local web foundation with email-OTP/TOTP registration, optional encrypted SQLite identity/role persistence, mock/V4L2 adapters, read-only dashboard and bounded role requests; AP/captive portal and live device deployment remain unverified |
| ESP32/GPS | archived firmware snapshot only | No active firmware source, verified board identity or flash evidence |
| Evidence/docs | `docs/` | Architecture, scope and report trail present |

Ownership and dependency rules are documented in
`docs/architecture/14_MODULE_BOUNDARIES.md`.

## Requirement-by-requirement status

| Requested feature | Status | Evidence / gap |
|---|---|---|
| PC is central public server | PARTIAL | FastAPI is live in PUBLIC mode behind a temporary quick tunnel; a permanent domain/reverse proxy/monitoring setup is still required |
| Public unauthenticated view | PARTIAL | Public map view works; no login means read-only public data |
| Map similar to `cambay.mod.gov.vn` | PARTIAL | Leaflet/OpenStreetMap base, zoom, legend, popup, coordinate/name search, distance measurement, browser location, coordinate grid and fullscreen are live; official basemap/data and geocoding are not configured |
| Pre-drawn no-fly/restricted zones | PARTIAL | Public endpoint is intentionally empty after removing test fixtures; Owner-created source plus Operator/Admin/Owner editor now explicitly chooses PUBLIC or INTERNAL visibility, and public-zone propagation is covered by a test; real records still require Owner bootstrap |
| Draw/edit/delete zones | PARTIAL | Backend CRUD + RBAC + geometry validation and click-to-draw/GeoJSON UI exist; official source import is not implemented |
| Account approval tab | PARTIAL | Backend account-review routes, capability policy and authenticated review tab exist; role-elevation request/review UI is now connected; real Owner approval still requires bootstrap |
| Flight-permission review tab | PARTIAL | Canonical `PC_INTERNAL_V1` workflow, encrypted applicant/license/vehicle/GPS form and review tab exist; external authority adapter is intentionally absent and responses are explicitly not government permits |
| Register + terms + email OTP + TOTP | PARTIAL | Staged login/register flow, terms, email OTP, TOTP enrollment/verification and recovery codes exist; operator still must bootstrap the first Owner |
| Default owner account | UNVERIFIED | Safe production bootstrap CLI and Gmail SMTP are configured; no Owner was created automatically because no password was invented on the server |
| Pi Wi-Fi/AP/captive portal | PARTIAL | Edge package is separated, but real AP/STA/captive-portal setup is not deployed or verified |
| Pi USB webcam | PARTIAL | Authenticated bounded camera status/frame routes and mock/V4L2 adapters exist; USB hardware is unverified |
| Pi map without zone editing | PARTIAL | Edge dashboard reads map cache and exposes no zone mutation route; PC sync and live cache provenance remain to be validated |
| Pi telemetry/3D/admin/firmware tabs | PARTIAL | Dashboard surfaces telemetry/3D, local USER->ADMIN request/review with CSRF/RBAC, and explicitly locked actuator/firmware actions; persistent role review, live telemetry and signed firmware workflow are missing |
| GPS GPIO16/17, 38400, NMEA/UBX | UNVERIFIED | User-provided wiring facts; no live UART capture or board-level evidence |
| ESP32 GNSS + flight-mode changes | MISSING | Firmware is archived; no active build/flash/test evidence |
| Approval sends arm; rejection blocks arm | SAFETY-GATED / MISSING | Canonical PC API intentionally has no ARM/DISARM endpoint; do not add until hardware safety design and bench evidence exist |
| Send encrypted flight request + GPS to authority | MISSING | Only simulated local workflow exists; no external authority endpoint or cryptographic exchange |
| Firmware update from manufacturer | MISSING | No signed artifact, authorization, rollback or recovery flow |
| Clean deployment/update process | PARTIAL | PC source and frontend deploy; deployment revision is not tied to an immutable commit/hash |

## Runtime verification

- Public web: HTTP/HTML and API health returned successfully.
- Public dashboard: API online and Leaflet map rendered with zero public zones after test-fixture cleanup.
- Pi edge tests: **21 passed** in the focused suite; the full repository run is **72 passed, 1 warning**. Coverage includes bounded HTTPS PC→Pi map synchronization, default-account email setup, email/login challenge rate limits, SMTP login-OTP delivery/rollback, server-enforced terms acknowledgement, encrypted identity/role persistence, registration email-OTP/TOTP, registration rate limiting/SMTP rollback, redacted Admin user listing, authentication gates, bounded camera frame access, read-only routes, wildcard-bind rejection, malformed-body handling, request-size limits, mandatory TOTP/replay rejection, account-bound factor lockout after the maximum failed code attempts and USER->ADMIN CSRF/RBAC review; no hardware claim is made.
- Public health: `environment=production`, `runtime_mode=PUBLIC`, `local_only=false`, `airspace_source_configured=false`.
- Public response headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and `Permissions-Policy` verified; geolocation is limited to the same origin.
- Authentication rate limiting is bounded and expires stale in-process entries; multi-worker deployment still requires a shared limiter before horizontal scaling.
- Flight-request idempotency digests now include encrypted applicant/license/vehicle/GPS details; a changed PII payload with the same key is rejected and covered by a regression test.
- PC and Pi flight-request forms now require a validated license class: `A` for visual flight or `B` for instrument/out-of-visual-line-of-sight flight. Both APIs enforce the same A/B constraint.
- Zone mutations now refresh the public map in the same authenticated page, avoiding stale public data until a full reload.
- Flight requests now require non-empty identity fields and paired GPS coordinates; incomplete submissions return validation errors.
- FastAPI schema validation errors now use the same versioned envelope as other API errors, without echoing submitted field values.
- Unused legacy frontend modules were removed from the active bundle, including stale fake telemetry/geofence/land-command clients; the active UI now contains only routes backed by the current PC API.
- Vite preview now has an explicit host allowlist and workflow headers. The public web uses same-origin API calls; direct backend CORS remains allowlisted, while temporary tunnel preflight behavior is not treated as production CORS evidence.
- The authentication modal now disables credential submission until terms are accepted, while the server-side terms check remains authoritative; this was verified in the public browser.
- The PC registration modal now requires explicit acknowledgement that the TOTP secret and one-time recovery codes were saved, closes the temporary enrollment session, and requires a fresh login after registration; this matches the pending-account workflow.
- The PC and Pi simulator interfaces now share a light sky-blue/white visual theme with higher-contrast controls, cards and status states; the local Pi page and public PC page were both reloaded and visually checked after deployment.
- The public PC overview now intentionally presents only the requested public map experience: the old connection button, runtime/status cards and empty-source notice were removed. Runtime mode, backend port and API documentation remain operational/developer concerns rather than visitor-facing content.
- The PC authentication dialog now uses the white/sky-blue reference layout and a dedicated high-priority stacking context (`z-index: 2000`); Leaflet panes, controls and legends can no longer render above the login form. The Pi login card uses the same visual language, keeps server-enforced terms acknowledgement, and routes `EMAIL_SETUP_REQUIRED` into the email setup form without a separate default-account button.
- The public Vite gateway now emits `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` and a restrictive CSP; the public HTML response was rechecked after restart.
- MFA failure counters now expire, are bounded and are keyed to the account instead of abandoned session IDs/client keys; a fresh staged login cannot bypass the five-attempt factor lockout window. Regression coverage exists for both PC and Pi.
- Login email challenges are now bound to the exact staged session that requested them, preventing a valid OTP from being replayed across concurrent login sessions; a regression test covers the cross-session rejection.
- Email challenges and recovery codes now use database compare-and-set consumption, and TOTP verification rejects replayed or older time steps; regression coverage protects against concurrent reuse and step rollback.
- Public mode now rejects `TEST_FIXTURE` sources on zone writes and disables the fake-Pi adapter routes; the production guard is covered by a regression test.
- The public UI now reflects `airspace_source_configured=false` honestly instead of implying an operator source is active; this was checked against the live public page.
- CSP `connect-src` was tightened from a wildcard `wss:` allowance to the configured public hostname plus local development hosts; the resulting live header and browser console were rechecked.
- The authenticated workspace now consumes server-provided effective RBAC capabilities before showing account/role-review tabs, so delegated-admin scope is reflected in the UI instead of showing actions that the backend must reject.
- Zone editing now preserves the selected zone's provenance and exposes an explicit source selector when multiple source records exist, preventing accidental reassignment to the first source.
- Map draft state is now reset when switching zones or starting a new edit, preventing an unfinished polygon from being silently carried into another zone.
- Starting or clearing an incomplete map draft now invalidates the old GeoJSON and disables save until a new polygon or explicit JSON is present.
- The flight-request form now checks time ordering and complete/finite GPS triples before sending, matching the backend contract and giving the operator actionable errors.
- The level-2 `OPERATOR` role now has backend/UI zone CRUD plus flight-review access while remaining blocked from account review; active `GUEST` users request `OPERATOR` first and only Owner-approved role elevation changes the role.
- Duplicate registration responses no longer disclose a specific email-in-use code/message and are covered by a regression test; the endpoint still returns a conflict status for client UX, so a fully uniform registration response remains a separate product decision. Switching between login and registration also clears the terms acknowledgement so each flow requires an explicit confirmation.
- Health now reports an Owner-managed `OPERATOR_DRAWN` airspace source as configured, not only an external source URL; this keeps the public status banner aligned with the actual source registry.
- All `/api/v1` responses now carry `Cache-Control: no-store`, not only authentication routes, so encrypted-flight workflow metadata and internal review responses are not retained by an intermediary cache.
- CSRF enforcement is now centralized in the authenticated session resolver, so every cookie-authenticated state-changing route is protected instead of only logout; bearer-token OTP stages remain compatible, and a role-elevation regression test covers the missing-token case.
- Login no longer reveals whether a correct-password account is rejected, suspended or incomplete for email/MFA setup; those cases use the same rate-limited authentication failure envelope as unknown credentials.
- Registration now has a separate bounded per-client rate limit in addition to the email-keyed authentication limiter, reducing OTP-mail abuse through many different email addresses.
- Login OTP issuance after a valid password is separately rate-limited, and recovery-factor attempts have their own bounded failure limiter; this prevents a correct-password session from becoming an unrestricted mail/second-factor oracle.
- Request bodies are bounded at both the PC and Pi web boundaries; audit/history metadata recursively redacts credential, token, OTP, recovery and cookie-like fields before persistence.
- The fake Pi adapter is now available only when the explicit non-public `ENABLE_TEST_ADAPTERS` flag is enabled; non-public mode alone is not sufficient to expose test routes.
- Terms acknowledgement is bound to the configured `TERMS_VERSION`, and the flight-review workflow rejects self-review by the request submitter.
- Credentialed CORS configuration now fails closed when `ALLOWED_ORIGINS=*` is supplied; wildcard origins are rejected at settings/app construction time.
- Local frontend: `npm run typecheck` PASS; `npm run build` PASS.
- Local Python: `python -m compileall -q server` PASS.
- Local full pytest after the security, workflow and Pi simulator updates: **72 passed,
  1 warning**.
- Production Gmail SMTP authentication and a direct OTP test message were
  successful; secrets remain in the remote mode-600 `.env`, not in source.
- Remote Alembic database is at migration head `d4a7f1c8e2b0`.
- Remote restart helper was exercised successfully; backend/frontend PID files now point to the actual live processes and health remained `200` after restart.
- Public frontend was black-box checked after restart: Cloudflare Host header returned HTML `200`; `/api/v1/health` returned JSON `200`. The preview allowlist, frontend working-directory issue and Windows-to-Linux executable-bit issue were fixed in `ops/pc/restart.sh` (Vite is invoked through `node`).
- Dependency/runtime checks: `npm audit --omit=dev --audit-level=high` reported 0 vulnerabilities; `pip check` reported no broken requirements. Direct backend CORS checks were limited to the configured origin; the temporary public tunnel was verified through same-origin browser/API checks rather than used as a production CORS proof.
- Local Python compileall completed successfully for `edge`, `server`, `ops` and `tests`; the frontend typecheck and production build completed successfully.
- Remote deployment is source-synced but is not tied to an immutable Git
  revision because this workspace is not a Git repository.
- `ops/pc/restart.sh` now performs readiness checks against the backend health
  endpoint and frontend root before reporting a successful restart; the
  updated helper was exercised on the remote PC and both checks passed.
- The restart helper now also verifies that the backend/frontend ports are
  actually free after stopping the recorded processes, preventing a stale
  Vite process from being mistaken for a successful deployment.
- The helper now matches the actual `vite.js preview` command line and has a
  port-scoped fallback for a live listener left without a PID file; the latest
  remote restart passed with fresh backend/frontend PIDs and the new frontend
  bundle was verified through the public browser.
- Public frontend deployment was corrected to update `frontend/dist/`, which
  is the directory consumed by Vite preview; the public browser then showed
  the new map disclaimer/build instead of the previous cached bundle. Stray
  root-level copied assets were removed from the remote frontend directory.

- The Pi local simulator now exercises the flight-request form/API with
  validated date/time/GPS fields and an explicit `PENDING_PC_REVIEW`,
  `NOT_A_GOVERNMENT_PERMIT`, `arm_state=BLOCKED` result. It does not contact
  an external authority or create an ARM command.
- The Pi login surface no longer exposes a separate "default account has no
  email" button or a checkbox-style terms control. Login submits the existing
  server-enforced terms version, and an `EMAIL_SETUP_REQUIRED` response
  automatically routes the default account to the email setup form while
  carrying the already-entered username/password locally in the page.
- Pi login now requires both the single-use email OTP and a single-use TOTP
  code; a replay regression test covers reuse of the same TOTP time-step.
- The local Pi camera UI now has an explicit laptop-webcam preview using browser
  `getUserMedia`; it remains local to the browser and does not change the
  server's mock/V4L2 camera contract.

## Decision

The project is correctly partitioned for a PC-first continuation, but it is
not yet compliant with the full requested system. The PC runtime and Pi edge
read-only foundation are now a
working, security-hardened local simulation boundary rather than a real
Ministry/authority system. The next PC gates are: bootstrap/approve the Owner,
publish operator-owned airspace data, finish advanced map interactions and
replace the local simulated permit decision only after an approved authority
contract exists. Pi and ESP32 work must remain behind their module boundaries
until hardware identity and safe test conditions are verified.
## Latest audit pass — 2026-09-30

Additional source findings and changes:

- `server/app/api.py`: corrected the delegated level-2 policy so `OPERATOR`
  can create, edit and delete zones and review flight requests, while account
  and role approval remains restricted.
- `frontend/src/components/auth/AuthPanel.tsx`: modal locks page scrolling,
  prevents duplicate submit, supports backdrop close, and restores body state.
- `frontend/src/components/operations/OperationsWorkspace.tsx`: added the
  `NEEDS_INFORMATION` flight-review action.
- `ops/pi5/local_simulator.py`: simulator no longer persists the TOTP secret
  value in `runtime/pi-sim/admin-bootstrap.txt`.

Validation commands issued:

```text
.venv-local\Scripts\python.exe -m pytest -q tests/scope02/test_account_and_roles.py
.venv-local\Scripts\python.exe -m pytest -q tests
npm --prefix frontend run typecheck
npm --prefix frontend run build
.venv-local\Scripts\python.exe -m pip check
.venv-local\Scripts\python.exe -m compileall -q server edge ops
```

The current local validation has complete summary/exit-code capture. No real Pi,
ESP32, GPS, USB camera, AP/STA, signed firmware, authority API, or deployment
acceptance test was performed. Project status remains `NOT COMPLETE`.

### Pi firmware surface

The Pi dashboard now exposes a dedicated `Firmware` tab so the operational layout matches the requested module split. The action remains disabled until a signed manufacturer artifact, device identity check, and tested rollback procedure are configured. There is intentionally no firmware upload or ESP32 flash endpoint in this build.

## Latest verification pass — 2026-09-30

- Public endpoints after the latest frontend/backend restart: `/api/v1/health` 200, `/api/v1/public/zones` 200, and `/docs`, `/redoc`, `/openapi.json` 404. The latter three are blocked both by the public FastAPI configuration and by the Vite MPA gateway, so an unknown docs path cannot fall through to the SPA.
- Public browser accessibility tree confirms the requested hero text, the `Khu vực bay tổng hợp` map, no legacy status cards/button/empty-source notice, and the exact ownership footer `DỰ ÁN ĐƯỢC THỰC HIỆN BỞI PHẠM NGỌC TẤN VÀ PHAN VĂN ĐÔNG`.
- Fixed a challenge-flow logic bug: an OTP from a login challenge is rejected by the email-verification endpoint before compare-and-set consumption, and the same OTP remains usable by the correct login endpoint. Regression coverage: `16 passed` in `tests/scope01/test_auth_flow.py`.
- Corrected the level-2 RBAC path: `OPERATOR` can now create, edit and delete WGS84 zones and review flight requests, while account and role review remains denied. Focused RBAC/map verification: `13 passed`; the API and compiled frontend were deployed and public health remained 200.
- The PC map renderer now handles both GeoJSON `Polygon` and `MultiPolygon` records; search and edit selection use bounds across all component polygons instead of assuming a single ring set.
- The PC authentication modal now exposes the existing one-time recovery-code path after the TOTP step, with a separate text input and a return path to TOTP. The browser copy no longer describes a recovery code as an email OTP.
- The account-review UI now sends the required idempotency header and surfaces activation/API failures in the visible error banner instead of silently failing.
- Registration and login now expose a bounded “resend email OTP” flow. Registration resends are anchored to the pending challenge, login resends are bound to the exact staged session, the old challenge is invalidated after a successful send, and the same in-process OTP rate limits apply.
- Full local verification remains green: `74 passed, 1 warning`, frontend typecheck/build pass, Python compileall pass, `pip check` clean, and production frontend audit reports `0 vulnerabilities`.
- The latest public bundle was redeployed and verified from the public tunnel: the page serves `index-SfOK8fiQ.js`, the backend health endpoint returns `200` with `environment=production`, and the public map/header/footer render with no legacy status cards or owner-source notice.
- The public tunnel is a temporary deployment mechanism and is not a permanent production domain or service supervisor. Hardware-dependent requirements remain unverified as listed above.
- The deployed `.env` now persists the current non-secret `VITE_PUBLIC_HOST` value, so the supported restart helper retains the Vite host allowlist instead of reverting to a 403 after restart.
- Pi factor challenges now reject the correct code after the per-account failure threshold has been reached, even when a second client key is used; registration TOTP enrollment has the same bounded attempt policy. PC and Pi request middleware now enforce the body-size cap while receiving chunked requests, not only when a client supplies `Content-Length`.
- The authenticated PC workspace now loads the public map for an active ordinary `GUEST` instead of requesting restricted internal zones and failing the entire workspace with `403`; GUEST users can still submit flight requests and request role elevation while internal zone data remains restricted.
- The PC account-approval client now sends the backend-required idempotency
  key, so the Owner/delegated-Admin “Kích hoạt” action reaches the status
  workflow instead of being rejected before authorization.
- The frontend build now handles logout failures without pretending the session ended; the authenticated UI stays visible and reports the server error until the session is actually revoked.
- The authentication factor panel now distinguishes the email OTP help text from
  the TOTP help text, so the 2FA screen no longer incorrectly says that its
  code was sent by email.
- PC startup now fails fast when the database cannot be reached or the migrated `users` schema is missing; it no longer swallows startup exceptions and leaves a misleading healthy process.

## Latest verification pass — 2026-10-01

- Full local validation is green: **78 passed, 1 warning** with
  `.venv-local\Scripts\python.exe -m pytest -q`.
- Pi-focused validation is green: **23 passed, 1 warning**. Pi role-request
  persistence now rolls back its in-memory state when durable storage fails;
  a failed decision cannot leave an apparent ADMIN elevation behind.
- Pi camera frame responses now include `Cache-Control: no-store` in addition
  to the global security headers.
- The Pi authentication surface now removes the unused default-account button
  and checkbox control; a continuation notice remains visible while the API
  still enforces `terms_accepted` for every auth/setup request.
- Frontend `npm run typecheck && npm run build` passed. Production dependency
  audit reports **0 vulnerabilities** at the configured high-severity level.
- The exact supplied Drone Zone Check logo is now the active transparent PNG
  asset; the previous white logo background and obsolete SVG asset are absent
  from the active frontend build.
- Remote public deployment was restarted successfully. The live health check
  returns `200`, `environment=production`, `runtime_mode=PUBLIC`,
  `local_only=false`, and `airspace_source_configured=false`; public `/docs`
  remains `404` by design.
- The deployed frontend asset directory was cleaned so only the current
  hashed bundle, stylesheet, HTML entrypoint and logo remain.
- Zone update/delete and draft-flight edit now accept optional idempotency
  keys; the frontend sends them for retries after a network timeout, and
  regression coverage verifies replay with an old `If-Match` returns the
  original result without a second mutation.
- Registration now catches a concurrent database uniqueness race after the
  pre-check, rolls back the failed transaction and returns the same generic
  conflict response instead of exposing a 500.
- Vite production headers now remove localhost WebSocket/CORS allowances;
  only development mode retains local dev origins, and the live public CSP
  was verified to contain only the public hostname plus the map tile origin.
- The public browser was reloaded and verified for the exact hero/footer text,
  public read-only map, transparent logo, and absence of legacy status cards.
- Frontend administrative mutations now retain the same idempotency key across
  a retry for the same resource/version/payload fingerprint; this covers zone
  editing/deletion, source creation, flight review, account approval, role
  requests/decisions and scoped capability grants. Successful actions clear
  the browser key; changed input or version receives a new key.
- Latest frontend build deployed and verified: `index-D-Mk4tTl.js` with
  `index-Dn5D2fK_.css`; `npm run typecheck && npm run build` passed.
- Added database-level concurrency guards for pending role-elevation requests
  and active capability grants, with a safe `409` response when a concurrent
  insert wins. Production migration `e6c7d8f9a0b1` reached head on the PC;
  the public process was restarted and health remained `200`.
- Public-mode zone reads now exclude legacy `TEST_FIXTURE` provenance while
  isolated test mode keeps fixtures available for contract tests. A regression
  test covers a legacy fixture accidentally marked `PUBLIC`.
- Final post-change validation: **79 passed, 1 warning**, Python compileall
  passed, and the live public CSP/health response was rechecked after restart.

The overall project status remains `NOT COMPLETE`: no claim is made for live
Pi AP/captive portal, ESP32/GPS capture, USB hardware acceptance, signed
firmware, official airspace data or an external authority permit API.

## Latest verification pass — 2026-10-01 (GNSS parser)

- Promoted the safe GNSS/NMEA parser checks into the active test suite instead
  of leaving them only under archived/future-scope tests.
- The parser now accepts valid NMEA UTC timestamps both with and without a
  fractional-seconds part, applies nearest-day UTC rollover handling, and
  rejects latitude/longitude outside the NMEA limits of 90°/180°.
- Added active receive-only and passive-baud-probe tests. They verify the
  configured default of 38400 baud, no TX/configuration writes, safe disabled
  hardware defaults, checksum/staleness/sequence-gap handling, invalid
  coordinates, and unsupported UBX framing behavior.
- Full local validation is green: **88 passed, 1 warning**. Python
  `compileall` passed and `pip check` reports no broken requirements.
- This remains parser/contract validation only. No claim is made that GPIO
  16/17, a physical GNSS module, live ESP32 telemetry, or hardware flashing
  has been verified; real serial access remains disabled until wiring and
  board identity are explicitly confirmed.

## Latest verification pass — 2026-10-01 (Pi web telemetry boundary)

- Added a read-only `ReadOnlyGnssTelemetrySource` adapter for the Pi web
  telemetry contract. It accepts an injected line reader, maps GNSS states to
  the Pi UI states, and exposes 38400 baud as metadata without opening a
  serial device or sending configuration/control bytes.
- The adapter fails closed when no reader exists, when a reader times out, or
  when the injected reader raises; no invalid position is returned as a valid
  fix and no web 500 is produced by a reader failure.
- Added three adapter regression tests. Full local validation is now **91
  passed, 1 warning**, with Python `compileall` and `pip check` clean.
- The adapter is intentionally not bound to GPIO 16/17 or a guessed device
  path. Live hardware capture still requires verified board identity, wiring,
  permissions and an explicit receive-only device adapter.
- Pi telemetry now exposes GNSS transport metadata separately from the fix:
  `baudrate=38400`, with `rx_pin` and `tx_pin` remaining `null` until those
  pins are physically verified. The UI therefore cannot silently present
  unverified GPIO ownership as fact.

## Latest verification pass — 2026-10-01 (Pi UI, profile security and ESP32 USB boundary)

- Confirmed from `C:\Users\pnt21\Desktop\DO_AN_CN\mach\code\f450_esp32_mpu6500`
  that the firmware already contains NMEA/UBX GPS parsing and exposes GPS,
  attitude, altitude and power fields through its internal `/status` data. It
  does not currently emit a structured JSONL telemetry stream over the CP2102
  USB path, so the Pi must not display invented sensor values. The source also
  maps the GPS UART to GPIO34/32 while GPIO16/17 are the MTF UART; this pin
  assignment must be verified before hardware wiring is changed.
- Added the receive-only ESP32 USB contract and bounded JSONL decoder. It
  accepts an explicitly configured CP2102 path (`/dev/ttyUSB*`, `/dev/ttyACM*`
  or Silicon Labs CP210x `/dev/serial/by-id/...`), uses 115200 baud, limits
  frames to 16 KiB, validates ranges and rejects malformed, replayed or
  sequence-gap frames.
- The real Pi ASGI entrypoint now uses this ESP USB boundary. Without
  `SCOPE05_ESP_USB_DEVICE`, telemetry returns `ESP_USB_NOT_CONFIGURED` with
  unknown values. The PC simulator uses the same boundary instead of a mock
  telemetry source.
- The USB webcam remains separate: real Pi capture is V4L2 from the verified
  `/dev/video0` USB webcam; the PC simulator's laptop preview stays browser
  local and is never uploaded.
- Replaced Pi's raw map-only view with a visual SVG zone map, replaced the raw
  3D placeholder with a labeled F450 frame model, and made null orientation
  values render as `chưa có` instead of `0°`.
- Added a safe account menu and profile-update workflow. It requires CSRF,
  current-password reauthentication and a one-time email OTP; password hashes,
  TOTP secrets and license details are not returned by the admin list API.
- Full local validation after these changes is **103 passed, 1 warning**;
  Python compilation is clean. The local simulator is running at
  `http://127.0.0.1:8081/` with the mock camera and an explicitly unavailable
  ESP32 source, so it is suitable for UI/auth verification but is not evidence
  of live Pi, webcam or CP2102 hardware connectivity.
