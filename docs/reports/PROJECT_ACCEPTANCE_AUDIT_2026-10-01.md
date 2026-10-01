# Project acceptance audit — 2026-10-01

## Summary

This is a current-state audit, not a completion certificate. The public PC
host serves the redesigned map-first UI, but its deployed sign-in consent is
still missing the clickable terms link that exists in the current workspace
build. The PC API is reachable in `production/PUBLIC` mode with security
headers and docs hidden; however, its public zone list is empty and no
authenticated production email flow or real Pi/ESP hardware has been accepted.
Do not describe the system as production-ready or as an official government
service.

## Verified in this audit

| Area | Evidence | Result |
|---|---|---|
| PC frontend | `npm run build`; `npm run typecheck` after map-first redesign | PASS |
| Automated tests | `.venv\Scripts\python.exe -m pytest -q` after Owner bootstrap/activation regressions | 124 passed; one upstream Starlette deprecation warning. |
| Isolated PC API | Temporary SQLite, loopback only; migrations reached head | PASS; health and public zones returned 200; unauthenticated `/api/v1/auth/me` returned 401 |
| Public HTTPS | `costa-eden-licensed-authorization.trycloudflare.com` | Health is production/PUBLIC; HTTPS and security headers observed; `/docs` returns 404 |
| Public flight-zone data | `GET /api/v1/public/zones` | Empty list (`count: 0`), explicitly labelled simulated/non-official |
| Public release identity | Live root page/browser reload | Serves the redesigned map-first PC UI; current JS `/assets/index-8QKQQN7Q.js`, CSS `/assets/index-ZMZohuBn.css`. Remote index was backed up before both replacements under `/tmp/iot-index-before-20261001-redesign.html` and `/tmp/iot-index-before-20261001-final-headline.html`. |
| Public airspace source | Public health payload | `airspace_source_configured: false` |
| Brand asset | Current logo source is preserved unchanged | Requested background cutout is still pending; generated edit altered the mark, so it was not applied |
| PC browser UI | Public domain after deployment | Map-first landing page, public read-only status, zero-zone empty state, footer attribution, and sign-in modal visibly present. No authenticated login was submitted. |
| PC local release build | `npm --prefix frontend run typecheck` and `npm --prefix frontend run build`; browser QA on `127.0.0.1:4173` | Typecheck and production build pass (`index-CffhmLFE.js`, `index-CB87FYcx.css`). Sign-in modal opens; terms control opens the dialog with the required demo notice; console had no errors in the prior browser pass. This verifies the current workspace build, not the public deployment. |
| PC map-toolbar overflow follow-up (2026-10-01) | `frontend/src/experience.css`; latest frontend typecheck/build; full `.venv\Scripts\python.exe -m pytest -q` | Reworked the PC public map toolbar into constrained responsive grid columns; long status text wraps instead of forcing past the map edge, and switches to one column at tablet/mobile widths. Latest build emitted `index-BlVDt85I.js` and `index-BFQeDli3.css`; all 124 Python tests pass. Browser screenshot at the available 642px viewport confirms the map search/status stack fits. A direct 1440px browser measurement could not run because the project virtualenv lacks Playwright; desktop behavior is supported by the CSS breakpoints but is not claimed as browser-measured. |
| PC/Pi current local runtime availability (2026-10-01) | Listener inventory and direct `/health` probes | `4173` is the Vite frontend preview; `8082` is `pi-local-web` with camera unavailable; the required PC API on `8765` does not answer. Port `48765` belongs to the local C2C bridge, not the project API. No SMTP environment or project `.env` is configured. Therefore the PC login cannot be used for real sign-in in this session, and no usable test password is available. |
| Current dependency audit (2026-10-01) | `npm audit --omit=dev`; `.venv\Scripts\python.exe -m pip_audit`; Node static-server test | No known npm or Python package vulnerabilities; static-server regression test passes 1/1. Dependency scans do not replace deployment/runtime security review. |
| PC local full-stack runtime | Local preview `127.0.0.1:4173`; API health probe at `127.0.0.1:8765/health` | The preview renders the UI but currently shows an API-unavailable state because the PC API is not running on 8765. Do not treat the static preview alone as a runnable PC installation. |
| PC production static origin (2026-10-01) | `ops/pc/static-server.mjs`; `node --check`; `node --test tests/ops/static-server.test.mjs`; direct loopback smoke checks on 5173 | PASS for static serving, SPA route, API proxy contract against a mock API, unknown-host rejection (421), documentation hiding (404), public-host HSTS, and no-cache index. The real API was not running during smoke QA, so `/api` returned the expected generic 502. |
| Registration MFA completion (2026-10-01) | Backend auth-flow regression tests and PC sign-in browser UI | Fixed a logic gap: completing registration MFA now revokes the enrollment session atomically and clears auth cookies instead of silently authenticating a still-pending account. The UI no longer depends on a follow-up logout request that could fail after successful registration. Re-login remains a separate step. |
| PC Windows production launcher (2026-10-01) | `ops/pc/run-windows-production.ps1`; Windows PowerShell parser and launcher option guard | Added guarded Windows launcher paths for persistent SQLite/API and Node static frontend on loopback. It requires SMTP, production flags, explicit consent before migrating an existing database, supports `-BootstrapOwner` and `-ActivateBootstrapOwner`, strips secrets from the frontend build environment, and clears password/session key in `finally`, including pre-service failure. Syntax parsing and mutual-exclusion guard pass. Full service startup remains unverified because production SMTP/public-host settings are not configured. |
| First PC Owner bootstrap/activation (2026-10-01) | `server/cli.py`; new `tests/scope02/test_owner_cli.py`; 7 targeted tests and full suite | Regression coverage proves bootstrap creates only a PENDING Owner, writes verification OTP only to the explicit test outbox in tests, does not print/store the password, requires exact activation confirmation, and activates only with verified email + password + current TOTP; bad factors leave the account pending and unaudited. Windows launcher exposes those CLI operations without persisting SMTP credentials. |
| PC session/TOTP encryption-key persistence fix (2026-10-01) | Windows PowerShell executed the actual helper functions against a disposable temp directory; called key loader twice and inspected ACL | Replaced per-start random `SESSION_SECRET` with one stable, cryptographically random key encrypted using Windows DPAPI under the current account at ignored `server/data/secrets/session-secret.dpapi`. `icacls` restricts the directory/file to the current account, SYSTEM, and local Administrators. A real Windows round-trip across calls returned the same key, and the secret file ACL is protected from inheritance. Disposable test directory was removed. Full launcher restart and a production TOTP account round-trip remain unverified. |
| Pi local app | ASGI app on `127.0.0.1:8082`; `/health` and browser login page | Title/brand `F450 PNT PVD` and terms layout verified. Health says `local_only: true`, `read_only: true`; camera is `UNAVAILABLE` because `/dev/video0` is absent on this Windows host. This is not physical-Pi acceptance. |
| Pi UI browser acceptance (2026-10-01) | Isolated simulator on loopback port 8082, disposable admin identity, file-backed test OTP sink | Email OTP + TOTP login, account menu/profile dialog, and all six dashboard tabs loaded; browser console had no errors. Reported mock/no-device states correctly. This is UI/API simulator evidence only, not Pi hardware acceptance. |
| PC security/dependency checks (2026-10-01) | `npm audit --omit=dev`; `.venv\Scripts\python.exe -m pip_audit`; unauthenticated live API checks | npm and Python audits report 0 known vulnerabilities. Live `/api/v1/auth/me` returns 401 with `Cache-Control: no-store`; a request carrying an untrusted Origin receives no `Access-Control-Allow-Origin`; API docs return 404. Public zones are still empty. |
| Pi API documentation exposure | `/openapi.json`, `/docs`, `/redoc` on local ASGI app; regression test | All return 404 after disabling OpenAPI generation; `tests/scope04/test_pi_web.py`: 28 passed. |
| Pi login visual QA | Browser at `127.0.0.1:8082`, desktop and 390×844 viewport | Checkbox, consent text and terms link stay on one aligned row; no horizontal page overflow; browser console has no errors. |
| Pi production startup | Runtime configuration tests; one-time admin bootstrap tests | Production ASGI refuses to start unless trusted HTTPS is asserted, encrypted persistent account storage and SMTP sender are configured; first-admin bootstrap is one-time and does not embed default credentials. This validates configuration gates, not real TLS certificates or real email delivery. |
| Live Pi inventory (read-only, 2026-10-01) | SSH to the owner's online Pi; OS/service/network/USB/V4L metadata only | Raspberry Pi OS aarch64, 58 GiB root with 44 GiB free. WLAN is disconnected; no hostapd/dnsmasq/Pi web systemd unit or web listener is present. UVC webcam appears as `/dev/video0` (1920×1080 MJPG, 25 fps); no CP2102/USB serial device appeared. No camera frame was captured. Existing `scope04-pi-web` copy is dated Sep 25 and has no active web service. Its local self-signed `localhost` certificate expired Sep 26, so it is not suitable for the Secure-cookie login path. No Pi files were modified. |
| Deployed PC consent control | Fresh browser session on the public root and sign-in modal | The public site currently serves the redesigned map-first UI and security headers. Its consent phrase is plain text (no terms link); current workspace build has the clickable link and demo-notice dialog. Public `/login` resolves to the same SPA. This is a confirmed release mismatch, not a browser cache guess. |
| Public PC service recheck (2026-10-01) | Read-only GET `/api/v1/health` and `/api/v1/public/zones` over HTTPS; public browser AX tree | API returns 200 in `production/PUBLIC`; HTTPS includes HSTS and security headers. `airspace_source_configured` is false and the zone API returns `count: 0` with a simulated/not-official label. Public login consent still has no clickable terms control. This confirms service reachability, not official/complete airspace or authenticated account acceptance. |
| PC airspace-health truthfulness fix (2026-10-01) | `server/app/api.py`; `tests/scope01/test_health_and_contracts.py`; targeted 14 tests + full 117-test suite | Health no longer treats a configured `AIRSPACE_SOURCE_URL` as a live source. It reports persisted source metadata separately from public official-source geometry and explicitly returns `official_airspace_sync_state=NOT_IMPLEMENTED`. Regressions cover URL-only configuration, operator-only metadata, and official GeoJSON metadata with public geometry. This is workspace code only; the public server has not been updated. |
| Official airspace-source research (2026-10-01) | Ministry of National Defense public announcement and official `cambay.mod.gov.vn` portal | Official announcement describes GeoJSON data available on the portal and says the underlying database is managed under State-secret protection rules and updated periodically or on change. No supported machine API/contract was established. Do not scrape, invent, or republish data by treating the portal homepage as a feed; automated official synchronization remains unimplemented pending an approved endpoint/use policy. |
| PC release target discovery | Windows listener inventory, public host response, and `ops/pc/restart.sh` review | No listener exists on documented PC API/frontend ports 8765/5173; WSL is unavailable. The Linux-only restart script cannot run on this host. A local 9Router service listens on `0.0.0.0:20128`, while the Cloudflare tunnel process targets that port; however, a direct Host-header request to that service redirects to its dashboard and does not identify a safe project release origin. Do not repoint the tunnel or overwrite the route without identifying the approved site mapping. |
| Local tunnel-management sidecar | Read-only local listener inventory and 9Router login page | 9Router listens on all interfaces at port 20128 and its local login page discloses a default-password hint. Whether the admin surface is reachable via the public tunnel was not established. Treat the sidecar as an infrastructure security exposure: rotate its credential and restrict its bind/firewall/tunnel access before any broader PC exposure. No 9Router setting or credential was changed. |
| ESP32 sketch hardening (2026-10-01) | Source review and patch of the user-provided F450 sketch; Windows PnP serial-port inventory | Removed hard-coded Wi-Fi fallback credentials; Wi-Fi now fails closed without a local config. ESP HTTP `/status`, ARM/DISARM, reset, PID, and config routes now return 423 `REMOTE_CONTROL_DISABLED`; wildcard CORS was removed. Source-only change is not build-verified because Arduino CLI/PlatformIO are absent; no COM/serial device was present and no flash occurred. GPS GPIO16/17 still conflicts with this sketch's MTF01P UART assignment, while the sketch's prior GPS config used GPIO34/32. Exact wiring requires owner confirmation. Rotate the Wi-Fi credential previously embedded in source. |
| Current Pi SSH | Batch public-key SSH to the previously used host | Authentication denied; no current physical Pi USB/camera inventory was collected |
| ESP/GNSS | Current SCOPE-05 V3 report dated 2026-09-27 | Read-only ESP identity/build evidence exists, but exact GNSS revision, wiring, and UART selection remain unresolved; live capture/flash gate is blocked |

The official MOD publication says the portal at `https://cambay.mod.gov.vn/`
supports downloading zone data in GeoJSON, but this check did not establish a
stable machine-to-machine API contract. The publication also says the source
database is governed by State-secret protection rules and updated on a cycle
or when changes occur. No official geometry was copied, scraped, or invented;
integration/republication needs an approved data-handling and refresh policy.

## Requirements not yet proven complete

- Authenticated browser flow (register → email OTP → TOTP → approval → role-
  gated workspace) was not verified end-to-end against a configured real SMTP
  service or a deployed PC backend. The isolated Pi simulator verified its
  admin login/UI only; this is not production authentication evidence.
- Public frontend static deployment is verified on the configured root route.
  The public API is healthy, but authenticated browser workflows and account
  approval were not run against production.
- Public zone data is empty until an authorized operator configures a valid
  source or creates reviewed operator-drawn zones. The application must not
  imply that these are official airspace notices.
- The requested exact-logo transparent cutout remains unfinished. The original
  logo asset was preserved; a generated attempt changed the artwork and was
  rejected rather than copied into the project.
- Pi AP/STA, captive portal, USB webcam, and local authentication were not
  revalidated on the physical Raspberry Pi. The Windows-hosted ASGI service on
  `8082` is loopback-only and reports the camera unavailable; it does not prove
  that the Pi service is installed or autostarts. The previously used `8081`
  service is not running.
- No trusted HTTPS endpoint or certificate was tested for the Pi AP. The
  production guard requires `PI_HTTPS_TERMINATED=true` as an operator assertion;
  certificate trust, reverse-proxy behavior, and captive-portal browser
  compatibility remain unverified. Do not turn off Secure cookies to work
  around this.
- ESP32 telemetry over CP2102, live GNSS reception, exact board/pin ownership,
  and firmware update were not revalidated on hardware. No flash or actuator
  command was issued. The existing report still blocks these actions pending
  exact board/GNSS evidence and a reviewed bench procedure.
- Successful production SMTP delivery, backup/restore, deployment rollback,
  monitoring, and incident response have not been demonstrated for the current
  live host. Public-mode startup validation proves SMTP settings exist, not
  that OTP delivery succeeds end to end.
- ESP HTTP routes are fail-closed in the edited source, but this change has not
  been compiled or flashed. Keep ESP Web UI/network access disabled until a
  verified firmware build is available and the replacement USB contract is
  hardware-validated. This is not a proof that the currently flashed ESP binary
  received the fix.
- The F450 sketch currently assigns GPIO16/17 to the MTF01P UART while the
  requested GPS wiring is GPIO16/17; its existing GPS constants instead use
  GPIO34/32. Do not compile/flash a guessed pin map.

## Safety and security disposition

- Public pages expose only the public-zones endpoint; the unauthenticated
  `auth/me` API check returned 401. The live deployment returned HTTPS security
  headers and hid API docs.
- The application labels its flight workflow simulated and not a government
  permit. Server-to-ESP ARM/DISARM and firmware-write paths remain out of scope
  and must stay unavailable until a separate reviewed safety gate.
- Local QA used a temporary database and development-only configuration. No
  user credentials, SMTP secrets, or production data were used.

## Required next gates

1. Confirm an approved SSH key/access method and the exact deployment target
   before replacing/changing any existing public route. Key-only SSH failed in
   this session; do not expose a password as a command argument.
2. Configure and verify production SMTP and owner bootstrap using the approved
   secret store; do not use default or shared credentials.
3. Decide the authoritative airspace data source and provenance/refresh policy;
   otherwise have the authorized Owner create reviewed operator-drawn zones.
4. Run authenticated browser acceptance against a staging deployment and
   verify each role/permission boundary.
5. Complete Pi physical acceptance and the SCOPE-05 hardware evidence gate
   before enabling any camera, GNSS, telemetry, or firmware operation on real
   devices.
6. Reconcile the deployment against SCOPE-08 (TLS/proxy, backup/restore,
   monitoring, rollback, privacy/legal review) before calling the service
   production-ready.
