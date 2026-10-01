# DISPATCH — Challenger R6-1 (Adversarial Testing: Camera, Map, and Login UI)

## Working Directory
/home/pnt/IOT/.agents/challenger_r6_1

## Mandatory References
1. Original request: `/home/pnt/IOT/.agents/ORIGINAL_REQUEST.md` (section `## 2026-09-14T05:07:21Z`)
2. Worker handoff report: `/home/pnt/IOT/.agents/worker_r6_1/handoff.md`
3. Project Architecture: `/home/pnt/IOT/PROJECT.md`

## Task
Adversarially challenge and stress-test:
1. **Camera Stream (R1)**:
   - Challenge concurrent access to `/api/v1/camera/stream`: does opening multiple simultaneous streams crash the worker thread or leak memory?
   - Challenge auth validation: request stream without auth (must reject 401), request with invalid token, valid cookie, query param `?token=`.
   - Challenge frame integrity: verify valid JPEG SOI (`0xFF, 0xD8`) and EOI (`0xFF, 0xD9`) markers on all emitted frames.
   - Challenge snapshot: test `GET /api/v1/camera/snapshot` returns valid JPEG image.
2. **Admin Map (R1)**:
   - Challenge CSP headers: verify `https://tile.openstreetmap.org` and `https://*.tile.openstreetmap.org` are allowed in `connect-src` and `img-src`.
   - Challenge map status: verify `/api/v1/status` returns `map_ready: true`.
3. **Login UI (R4)**:
   - Verify label is "Tên đăng nhập:" and placeholder is "tên đăng nhập". Verify no remaining instances of "tài khoản pi5" exist in `frontend/src/`.

Write your stress tests / verification scripts and document results in `/home/pnt/IOT/.agents/challenger_r6_1/handoff.md` with a clear verdict: `APPROVE` or `REQUEST_CHANGES`. Send a completion message to parent when done.

## 2026-09-14T05:29:06Z
Adversarially challenge and stress-test:
1. Camera stream: concurrent clients, authentication variations (cookie, query param, missing/invalid auth), valid JPEG SOI/EOI markers on frames, snapshot endpoint.
2. Map & CSP: verify CSP headers permit tile.openstreetmap.org in img-src and connect-src; verify map_ready: true.
3. Login UI: verify "Tên đăng nhập:" and "tên đăng nhập" placeholder; search for any remaining "pi5" references on login forms.
Write your findings and test script results to /home/pnt/IOT/.agents/challenger_r6_1/handoff.md with a clear verdict: APPROVE or REQUEST_CHANGES. Send a completion message to parent when done.
