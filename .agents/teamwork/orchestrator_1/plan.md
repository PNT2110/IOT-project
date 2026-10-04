# Master Plan: IoT Drone Zone Management System (F450 PNT PVD)

## Objective
Execute end-to-end bug fixing, UI/UX improvements, and new feature implementation across all 3 tiers (PC server/frontend, Raspberry Pi 5 gateway/UI, ESP32 firmware) to production-grade quality, verified by tests, typecheck, review, challenger, and forensic audit.

## Phases

### Phase 0: Full Scope Survey (Current)
- Spawn 3 parallel Explorers:
  - `explorer_survey_1`: Firmware & Pi Gateway Tier (`firmware/`, `edge/pi5/`, `tests/firmware/`, `tests/scope05`)
  - `explorer_survey_2`: PC Server Backend Tier (`server/app/`, `tests/scope01`–`07`)
  - `explorer_survey_3`: PC Frontend Tier (`frontend/src/`, `frontend/package.json`, styles, typecheck)
- Outcome: Exhaustive mapping of existing code, interfaces, tests, bugs, and feature integration points.

### Phase 1: Synthesis & PROJECT.md
- Merge survey findings into `PROJECT.md` at project root.
- Establish Feature Inventory, Architecture, Code Layout, Interface Contracts, and Milestones (3-7 milestones).
- Establish Dual Track strategy: E2E Testing Track + Implementation Track.

### Phase 2: Dual Track Launch
- Track 1 (E2E Testing Track): Spawns E2E Testing Orchestrator / test writers for opaque-box test infra and cases (Tiers 1-4). Publishes `TEST_READY.md`.
- Track 2 (Implementation Track):
  - Milestone 1: Confirmed Bugs Fixes (Altitude limiter dynamic floor, non-blocking SMTP, email normalization).
  - Milestone 2: Server Backend New Features (Telemetry ingestion & real-time streaming/SSE/WS, flight request notifications, GeoJSON/CSV export).
  - Milestone 3: PC Frontend UI/UX & Features (Dark mode, loading states/spinners, 8s auto-dismiss error banners, real-time telemetry view, flight request notifications, export buttons, strict typecheck).
  - Milestone 4: Pi 5 Gateway & Local UI (Modular component refactoring, camera pause/resume, OTA firmware update page).
  - Milestone 5 (Final Milestone): Phase 1: 100% E2E test pass (Tiers 1-4); Phase 2: Adversarial coverage hardening (Tier 5 challenger loop).

### Phase 3: Gate & Forensic Audit
- Strict gate criteria per iteration: Build & tests pass, 2 Reviewers APPROVE, 2 Challengers APPROVE, 1 Forensic Auditor CLEAN. Zero tolerance on integrity violations.

### Phase 4: Final Reporting & Handoff to Sentinel
- Full synthesis and completion report sent back to Sentinel.
