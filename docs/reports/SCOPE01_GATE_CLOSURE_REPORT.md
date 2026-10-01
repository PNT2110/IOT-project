# SCOPE-01 — Gate closure report

**Captured:** 2026-09-22T04:28:06+07:00  
**Repository:** `/home/pnt/IOT` · branch `main` · HEAD `16dc418076b1a53a9d2fc9af482e3a514f0791f7`  
**Scope:** PC Server Foundation, local-only. No Pi, ESP32, GNSS, firmware, public bind, tunnel or real airspace source was used.

## Final gate result

`PASS` for the mandatory SCOPE-01 acceptance gates in `docs/scopes/SCOPE01_SERVER_FOUNDATION.md`.

The historical `PARTIAL` result is preserved in the earlier final report. This continuation closes the previously missing trusted-browser HTTPS and Python-audit gates, adds the missing browser-facing auth/dashboard path, fixes cookie logout CSRF enforcement, and adds regression coverage. SCOPE-02 remains closed until owner acceptance.

## P0 baseline and protection

The repository was re-baselined before edits:

| Check | Evidence |
|---|---|
| Working directory/root | `/home/pnt/IOT` |
| Branch/HEAD | `main` / `16dc418076b1a53a9d2fc9af482e3a514f0791f7` |
| Existing dirty state | `.gitignore` and `docs/05_SYSTEM_ARCHITECTURE.md` modified; SCOPE-00 docs and prior SCOPE-01 implementation files untracked; preserved |
| Firmware archive | `FC_can_bang.zip` preserved read-only; prior SHA-256 `95809c58d61bb20c12a9541719ad90ec4afc8dab74597a20517486174849771f` |
| Runtime artifacts | No `server/data` DB, `.db`, `frontend/node_modules` or `frontend/dist` is tracked; local runtime paths are ignored |
| Destructive Git actions | None; no reset, clean, checkout, stash, commit or push |

New/modified paths in this gate-closure continuation are limited to:

- `server/app/api.py`, `config.py`, `mail.py`, `main.py`, `server/cli.py`, `server/README.md`;
- `server/requirements.txt`, `server/requirements.lock`, `.env.example`;
- `frontend/vite.config.ts`, `frontend/src/api.ts`, `frontend/src/App.tsx`, `frontend/src/styles.css`, `frontend/package.json`, `frontend/package-lock.json`;
- `tests/scope01/browser_e2e.py` and expanded `tests/scope01/test_*.py`;
- this report and append-only addenda to the existing SCOPE-01 reports.

## Requirement and acceptance matrix

| Requirement/acceptance | Evidence path | Test/evidence | Status |
|---|---|---|---|
| Guest sees only public synthetic fixture | `server/app/api.py`, `frontend/src/App.tsx` | `test_public_api_does_not_expose_internal_fixture`; browser guest request to internal API returns `401` | PASS |
| Public label is explicit | `server/app/services.py`, `frontend/src/App.tsx` | API response label and browser SVG text | PASS |
| Register → email verification → TOTP enrollment → recovery codes | `server/app/api.py`, `frontend/src/App.tsx` | `test_registration_email_totp_and_login_chain`; trusted browser E2E | PASS |
| Login password + terms + email OTP + TOTP | `server/app/api.py`, `frontend/src/api.ts`, `App.tsx` | API chain and trusted browser E2E | PASS |
| OTP TTL/replay/attempt limit | `EmailChallenge`, `_challenge_or_error` | `test_email_challenge_replay_and_attempt_limit_are_enforced` | PASS |
| TOTP invalid/replay/rate limit | `_factor_rate_limit_check`, `_factor_failure` | `test_invalid_totp_does_not_complete_auth` | PASS |
| Secure session cookies and logout CSRF | `_set_auth_cookies`, `_require_csrf`, logout route | API regression plus browser cookie inspection and missing-CSRF `403` | PASS |
| Session expiry/revocation | `_session` | `test_expired_session_is_rejected`; browser logout flow | PASS |
| Owner bootstrap does not bypass factors | `server/cli.py`, `server/app/mail.py` | `test_owner_bootstrap_has_a_complete_local_email_mfa_path`; owner remains `PENDING` after MFA | PASS |
| Account approval | `User.status`, dashboard boundary text | Approval is explicitly outside SCOPE-01 and reserved for SCOPE-02 | DEFERRED BY SCOPE |
| RBAC: pending cannot read/mutate internal map | `_require_map_read/write` | pending negative test and browser/API negative check | PASS |
| Admin mutation/audit/version guard | zone routes, `record_audit` | CRUD test with stale `If-Match` and three audit records | PASS |
| Invalid GeoJSON and WGS84 bounds | `server/app/geo.py` | invalid geometry test | PASS |
| Object-not-found/IDOR enumeration response | zone route `404` envelope | `test_unknown_zone_does_not_leak_object_details` | PASS |
| Search/official tiles | React demo canvas | Search remains deferred; no external or unlicensed tiles are used | DEFERRED BY DECISION |
| SQLite migration/backup/restore | `server/migrations/` | clean/repeated upgrade, downgrade/upgrade, copied backup restore | PASS |
| API envelope/OpenAPI boundary | `server/app/main.py`, `contracts/v1/README.md` | health/contract tests and route scan | PASS |
| No Pi/ARM/DISARM/flight-permit path | API/OpenAPI and source boundary | control-route scan | PASS |
| Loopback-only bind | `config.py`, run command | Uvicorn smoke and `ss -ltn`: `127.0.0.1:<runtime-port>` only | PASS |

No non-overlap invariant is defined for synthetic research polygons in the current SCOPE-01 contract; overlap enforcement is intentionally not invented. If the owner requires it, it is a future domain decision, not a hidden claim of coverage.

## Trusted HTTPS browser E2E

Command executed:

```bash
SCOPE01_CERTUTIL=/tmp/scope01-nss.LHkUYj/root/usr/bin/certutil \
SCOPE01_CHROME=/usr/bin/google-chrome \
.venv/bin/python tests/scope01/browser_e2e.py
```

Environment and trust isolation:

1. The test generated a one-day CA and `localhost` certificate in a temporary directory with `openssl`.
2. `libnss3-tools` was downloaded and extracted to `/tmp`; it was not installed system-wide.
3. `certutil` imported only the test CA into a temporary `HOME/.pki/nssdb` used by the isolated Chrome profile.
4. The real user home, system trust store and personal Chrome profile were not changed.
5. Playwright used real Google Chrome `153.0.8010.36` and did not set `ignoreHTTPSErrors`, `--ignore-certificate-errors`, `--allow-insecure-localhost` or an HTTP fallback.
6. The API and Vite UI selected free runtime ports and both server processes were stopped in `finally` cleanup. Private test keys/CSR/serial files were removed; the screenshot was retained.

Result: `PASS`, exit code `0`.

Evidence: [scope01-authenticated-dashboard.png](/tmp/scope01-browser-e2e-qlpvqx66/scope01-authenticated-dashboard.png)

Browser assertions included public map visibility, unauthenticated internal API denial, registration, fake-mail verification, TOTP enrollment, pending dashboard, `Secure`/`HttpOnly`/`SameSite=Lax` cookies, absence of the session cookie from `document.cookie`, empty `localStorage`, CSRF denial without the header, logout, staged login with email OTP and TOTP, and pending-role internal API denial.

## Dependency and warning audit

| Component | Command/result |
|---|---|
| Python dependencies | `pip-audit 2.10.1 -r server/requirements.lock`: `No known vulnerabilities found`, exit `0` |
| npm dependencies including dev | `npm --prefix frontend audit --audit-level=high`: `0 vulnerabilities` |
| npm production dependencies | `npm --prefix frontend audit --omit=dev --audit-level=high`: `0 vulnerabilities` |
| Starlette/TestClient warning | `httpx2==2.13.0` added per Starlette guidance; the warning disappeared |
| Remaining warning | One upstream `anyio.abc.BlockingPortal` deprecation emitted by Starlette `1.6.0`; no application failure or security bypass; keep as dependency maintenance debt |

The Python audit covers the pinned application lockfile, not OS packages, Chrome, OpenSSL or the temporary audit/browser tools. npm audit is advisory-database coverage for the resolved npm tree, not a complete supply-chain or license review.

## Test and runtime evidence

- `.venv/bin/pytest -q tests/scope01 -W default`: `13 passed, 1 warning`, exit `0`.
- `.venv/bin/python -m compileall -q server tests/scope01`: PASS.
- `npm --prefix frontend run typecheck`: PASS.
- `npm --prefix frontend run build`: PASS, Vite `7.3.6`.
- Alembic clean/repeated upgrade, downgrade/upgrade and backup-copy restore: PASS; restored revision `380891b589d3`.
- Local smoke: `/api/v1/health` returned `local_only=true` and request ID; public zones returned one synthetic item and the explicit label.
- Bind evidence: `LISTEN ... 127.0.0.1:8765`; no `0.0.0.0:8765` or `[::]:8765`; port was clean after teardown.
- `git diff --check`: PASS.
- Boundary/secret scans: no control route or private-key/API-key pattern found in application/config paths.

## Known bounded deviations

- The map is a React SVG demo canvas; search and authorized tile/PMTiles integration remain deferred.
- Fake mail is an in-memory adapter by default. Owner bootstrap requires an explicitly configured local `FAKE_MAIL_OUTBOX`; it does not print or bypass OTP/MFA and is not a real provider.
- The TOTP limiter is process-local, appropriate only for this local foundation; distributed/session-store hardening belongs before any non-local deployment.
- Account approval and workflow remain SCOPE-02; the SCOPE-01 dashboard explicitly shows `PENDING` and does not grant internal access.
- No real airspace/legal source, Pi, ESP32, GNSS, camera or actuator path was accessed.

## Rollback for this continuation

Remove or revert only the gate-closure changes listed in the P0 manifest: the auth/UI hardening in `server/app/` and `frontend/`, fake-mail outbox support, test runner and expanded tests, dependency pin changes, `.env.example`, README update and this report/addenda. Preserve the earlier SCOPE-00 docs, prior implementation and all retained test evidence unless the owner explicitly requests otherwise. No Git rollback command was run.

## Stop condition

SCOPE-01 gate closure is complete. Wait for owner acceptance. Do not start SCOPE-02, connect to Pi/ESP32/GNSS, flash firmware, issue ARM/DISARM, use real authority data or expose the server publicly.
