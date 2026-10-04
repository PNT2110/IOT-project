# Original User Request

## 2026-10-03T20:35:14Z

Fix all identified bugs and implement comprehensive UI/UX and feature improvements for an existing IoT drone zone management system (F450 PNT PVD). The project has a 3-tier architecture: a PC server (FastAPI backend + React 19 frontend), a Raspberry Pi 5 gateway (FastAPI + Vanilla JS UI), and ESP32 firmware (C++ flight controller). The goal is production-grade quality — all changes must integrate cleanly with the existing codebase, preserve the existing test suites, and follow the project's established conventions (Vietnamese comments, TypeScript strict mode, contract-driven API design).

Working directory: c:\Users\pnt21\Desktop\IOT
Integrity mode: development

## Reference Material

A full project audit has been completed. Key findings:

**Confirmed Bugs:**
- `firmware/FC_can_bang/flight_gate.h` lines 59–83: The `altitude_throttle_cap()` function reduces throttle to a hard floor of 1100 µs (`ALT_LIMIT_FLOOR_US`). For a heavily loaded F450 drone, 1100 µs is below hover throttle, causing uncontrolled descent. The barometer module exists (`Baro.ino`) but is not integrated into altitude limiting.
- `server/app/mail.py` lines 61–71: `SmtpEmailSender.send_code()` uses synchronous `smtplib.SMTP(timeout=15)` inside an async FastAPI application, blocking the entire event loop for up to 15 seconds.
- `server/app/security.py` line 27–28: `normalize_email()` only applies `strip().casefold()`, missing Gmail dot-stripping and subaddress (`+tag`) handling, allowing duplicate accounts from the same real email address.

**UI/UX observations:**
- CSS variables in `frontend/src/styles.css` and `frontend/src/experience.css` already define a complete design token system (`--ink`, `--surface`, `--canvas`, etc.) that is ready for dark mode via media query.
- `frontend/src/components/operations/OperationsWorkspace.tsx` uses a `busyAction` state for disabling buttons but shows no visual loading indicator (spinner/skeleton) during initial data fetch or long operations.
- Error banners in the frontend never auto-dismiss; they persist until the next user action clears them.
- The Pi 5 local UI (`edge/pi5/pi5/web/ui/app.js`) is a 589-line monolith using a HyperScript-like DOM builder (`h()` function) — untypeable and hard to maintain.

**Existing test infrastructure:** pytest test suites in `tests/scope01` through `tests/scope07` covering auth flows, RBAC, zones, flights, Pi features, device channels, and firmware. Firmware unit tests in `tests/firmware/`.

## Requirements

### R1. Fix all confirmed bugs
The three bugs listed in the reference material must be fixed. The altitude limiter must prevent uncontrolled descent without disabling altitude limiting entirely. Email sending must not block the async event loop. Email normalization must handle the most common aliasing patterns to prevent trivial duplicate account creation.

### R2. UI/UX improvements for the PC frontend
The PC frontend (`frontend/`) must gain: dark mode support that respects the user's system preference, visible loading states during async operations, and error banners that auto-dismiss after a reasonable interval while remaining manually dismissible. All changes must maintain the existing accessibility features (aria attributes, semantic HTML).

### R3. Pi 5 local UI modernization
The Pi 5 local interface (`edge/pi5/pi5/web/ui/`) must be refactored from the current 589-line monolithic `app.js` into a maintainable component-based architecture. The refactored UI must add a camera stream pause/resume control to reduce mobile bandwidth consumption.

### R4. New features
The system must gain four new capabilities:
1. A real-time telemetry display on the PC frontend that shows live GPS position, altitude, and battery data streamed from the Pi gateway.
2. A notification mechanism that alerts PC operators when new flight requests arrive.
3. An export function that lets operators download zone data and flight request history.
4. An OTA firmware update management interface on the Pi local UI for managing ESP32 firmware uploads.

### R5. Test coverage and quality
All bug fixes and new features must be covered by tests. Existing tests in `tests/scope01` through `tests/scope07` and `tests/firmware/` pass. New tests should follow the project's existing pytest conventions.

## Acceptance Criteria

### Bug Fixes
- [ ] The altitude limiter in `flight_gate.h` uses a dynamic floor that accounts for the drone's current state rather than a hard-coded 1100 µs floor. The existing unit tests in `tests/firmware/test_flight_gate.cpp` pass, plus new tests covering the improved limiter behavior.
- [ ] `SmtpEmailSender.send_code()` no longer blocks the event loop — verified by confirming the function is either natively async or wrapped in `asyncio.to_thread()` (or equivalent).
- [ ] `normalize_email()` strips dots before `@` for Gmail-family domains and removes `+suffix` subaddresses. A unit test demonstrates that `john.doe+test@gmail.com` normalizes to the same value as `johndoe@gmail.com`.

### UI/UX — PC Frontend
- [ ] Dark mode activates automatically via `prefers-color-scheme: dark` media query and produces readable, non-broken UI across all views (map, zones, flights, accounts).
- [ ] A loading spinner or skeleton is visible while `OperationsWorkspace` fetches initial data.
- [ ] Error banners auto-dismiss after 8 seconds but can also be closed manually with a dismiss button.
- [ ] All existing `aria-*` attributes and semantic HTML remain intact.

### UI/UX — Pi Local Interface
- [ ] The Pi local UI is split into multiple files/modules instead of a single monolithic `app.js`.
- [ ] A camera stream pause/resume button is functional on the Pi dashboard's camera view.
- [ ] The Pi UI's visual appearance and functionality remain equivalent to the current version (no regressions in features like network config, auth, telemetry display).

### New Features
- [ ] The PC frontend has a telemetry view that displays GPS coordinates, altitude, and battery percentage, updated in real time (within 2 seconds of data arriving at the Pi).
- [ ] PC operators receive a visible notification (on-screen badge, sound, or browser notification) when a new flight request is submitted.
- [ ] An export button lets operators download zone data as GeoJSON and flight history as CSV.
- [ ] The Pi local UI has an OTA firmware management page that can upload a `.bin` file and display upload status.

### Test & Quality
- [ ] All existing tests in `tests/scope01` through `tests/scope07` and `tests/firmware/` pass.
- [ ] New tests cover the bug fixes (altitude limiter, email normalization) and at least the core logic of each new feature.
- [ ] The frontend builds without TypeScript errors (`npm run typecheck` or `npx tsc --noEmit` passes).
