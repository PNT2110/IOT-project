# Master Orchestration Plan: IOT Drone Station v2 Upgrade

## 1. Objectives
Upgrade the IOT Drone Station to v2 based on `/home/pnt/IOT/prompt-du-an-drone-v2.md` and `/home/pnt/IOT/.agents/ORIGINAL_REQUEST.md`. Deliver all requirements (R1-R6), pass all 16 SSH test scenarios (table 12.1), satisfy all Definition of Done checklist items, conduct a security audit per section 13, and generate a comprehensive security risk report.

## 2. Phases
### Phase 0: Deep Survey & Spec Mining (3 Parallel Explorers)
- **Explorer 1 (Firmware & Serial)**: Probe `/home/pnt/IOT/FC_can_bang`, serial JSONL protocol, Wi-Fi AP + captive portal requirements, Pi5 handoff, ESP32 build system.
- **Explorer 2 (Pi5 Backend & Security)**: Probe FastAPI backend, user/role management, email OTP + TOTP 2FA, firmware upload/flash pipeline, ARM lock fail-safe logic, security checklist (passwords, SSH, ports, rate limiting).
- **Explorer 3 (Frontend & MOD Server)**: Probe React 19 UI (6 tabs transition, blue-white theme, 3D LiDAR telemetry), and design of the independent MOD server (auth, flight permits, dynamic 1km geofence, no-fly zone drawing).

### Phase 1: PROJECT.md & TEST_INFRA.md Synthesis
- Synthesize explorer findings into a comprehensive `PROJECT.md` with:
  - Feature Inventory (every single requirement mapped)
  - Architectural boundaries and interface contracts
  - Code layout conventions
- Setup `TEST_INFRA.md` outlining the 16 automated SSH test scenarios and multi-tier test harness.

### Phase 2: Dual-Track Execution
- **Track A: E2E Test Suite Orchestrator / Test Writer**
  - Implement test runner capable of testing Pi5 at `192.168.1.118` or local mock environment.
  - Implement tests 1 through 16 corresponding to Table 12.1.
  - Publish `TEST_READY.md`.
- **Track B: Implementation Milestones**
  - M1: ESP32 Wi-Fi Provisioning & Serial Communication (`FC_can_bang` logic).
  - M2: Authentication & Role Management (OTP email, PyOTP 2FA, admin mandatory setup).
  - M3: Firmware Flashing Pipeline & ARM Safety Locking (esptool/serial flash, arm lockout until flashed).
  - M4: 6-Tab Blue-White UI (Camera, Telemetry 3D+LiDAR, PID, Session, Map, FW Management).
  - M5: Independent MOD Server (REST API, web UI, flight permission approval, dynamic geofence).
  - M6: Security Hardening (SSH config, strong passwords, fail2ban/firewall review).

### Phase 3: Verification, Adversarial Hardening & Forensic Audit
- Run all unit and integration tests.
- Execute full 16 SSH automated test scenarios.
- Deploy Forensic Auditor (`teamwork_preview_auditor`) to ensure absolute authenticity and zero dummy code.
- Generate full Security Risk Report and document all implementation assumptions.

### Phase 4: Delivery & Handoff
- Produce `handoff.md`.
- Report to Sentinel via `send_message`.
