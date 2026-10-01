## 2026-09-13T09:32:12Z
Conduct a comprehensive, read-only survey of the frontend in `/home/pnt/IOT/frontend`, the design requirements for the standalone MOD Server, and the 16 automated SSH test scenarios.
1. Survey the existing frontend (`frontend/src`, components, router, state management, Vite config, package.json):
   - Current tab structure vs the required 6 tabs:
     1. Camera (USB camera stream)
     2. Telemetry & 3D model (Roll/Pitch/Yaw only + LiDAR altitude)
     3. PID Tuning (read/write serial)
     4. Current Session (logged-in user info)
     5. Map (drone position, active authorized flight zone)
     6. Firmware Management (update/flash new FW, delete current FW)
   - Blue-White theme requirement: assess current styling (Tailwind, CSS modules, etc.) and what changes are needed to unify with the blue-white theme.
   - Flight Permission Request button on the header (only visible to approved admin) -> modal (Full name, pilot license ID, flight date, time window from-to, current drone GPS).
   - Role-based UI visibility (User role can only see Camera tab).
2. Design & survey the independent MOD Server (Section 7):
   - Separate server architecture: what stack to use (FastAPI + lightweight frontend or standalone service), port, database.
   - Default admin account, user registration with admin approval.
   - Tabs: 1) Account & flight request management (approve/reject), 2) Draw/delete no-fly zones (GeoJSON/polygons).
   - Flight approval logic: 1km radius around requested GPS, valid only during specified time window, auto-closes when expired.
   - Communication between Pi5 and MOD server (REST API, TLS, replay attack prevention).
3. Investigate the 16 automated SSH test scenarios (Section 12, Table 12.1):
   - Enumerate all 16 test scenarios, their test methods, and expected results.
   - How an automated test harness (pytest or python script) can execute these tests via SSH (`pi5@192.168.1.118`) or local simulation.
   - What tools and fixtures are needed for end-to-end automation.

Deliverables:
Write your full investigation report to `/home/pnt/IOT/.agents/explorer_v2_survey_3/report.md`.
Include:
- Frontend component architecture and 6-tab migration plan
- Blue-white theme design specifications
- Independent MOD Server complete design (API contracts, database, UI, dynamic geofencing)
- Detailed breakdown of all 16 SSH test scenarios with automated verification strategies

When done, write `/home/pnt/IOT/.agents/explorer_v2_survey_3/handoff.md` and send a message to parent via send_message with a brief summary and path to your report.
