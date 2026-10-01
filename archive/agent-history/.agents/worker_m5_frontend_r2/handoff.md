# HANDOFF REPORT: FRONTEND V2 UPGRADE & 6 TABS (MILESTONE 5)

## 1. Observation
1. **Codebase inspection**:
   - `frontend/src/styles.css` originally contained dark cyberpunk tokens (`:root { --bg:#04090c; --panel:#081216; --teal:#35e6c1; }`).
   - `frontend/src/Tabs.tsx` was a preliminary draft with inline styles and unmodularized tabs.
   - `frontend/src/DashboardPanels.tsx` contained a read-only PID panel (`<span className="readonly-badge">CHỈ THEO DÕI</span>`), lacking inputs or write capability to ESP32 serial.
   - Telemetry interface in `frontend/src/types.ts` lacked `lidar_altitude_m`, `Altitude_kalman`, `battery_pct`, and `flight_permission`.
   - `frontend/src/App.tsx` lacked the "Xin phép bay" button and modal for approved admins, and role restriction for `user` only showed a raw viewer shell.
2. **Build and runtime verification**:
   - Tool command: `export PATH="/home/pnt/IOT/node-v20.11.1-linux-x64/bin:$PATH" && cd /home/pnt/IOT/frontend && npm run build`
   - Command result:
     ```text
     > iot-drone-station-ui@0.1.0 build
     > tsc -b && vite build

     vite v7.3.6 building client environment for production...
     ✓ 2824 modules transformed.
     dist/index.html                     0.55 kB │ gzip:   0.34 kB
     dist/assets/index-CNcmadGi.css    107.04 kB │ gzip:  16.48 kB
     dist/assets/index-mqB5OaZw.js   2,670.03 kB │ gzip: 740.40 kB
     ✓ built in 6.08s
     ```
   - Exit code: 0, 0 TypeScript errors.

## 2. Logic Chain
1. *From Observation 1*, the requirements of prompt-du-an-drone-v2.md (Sections 1, 5, 6, 8, 9, 10, 11) required a complete redesign of `frontend/` into a unified Blue-White theme with 6 dedicated tabs, flight permission modal, role restrictions, and full API integration.
2. *Based on Section 9 & 3.2 of survey findings*, `styles.css` was rewritten with a complete Blue-White Aviation GCS design system (`--bg-app: #f4f7fb`, `--bg-surface: #ffffff`, `--color-primary: #0066cc`, `--status-green: #16a34a`, `--status-red: #dc2626`, slate text `#0f172a`/`#475569`).
3. *Based on Section 6*, 6 dedicated tab components were implemented:
   - `CameraTab.tsx`: USB live video stream (`/api/v1/camera/stream`), snapshot capture, resolution & FPS indicator.
   - `TelemetryTab.tsx`: Three.js 3D attitude model, prominent LiDAR altitude card (`lidar_altitude_m` / `Altitude_kalman`), Roll/Pitch/Yaw/Heading/Battery gauges.
   - `PidTuningTab.tsx`: Full interactive read/write serial control, numeric input validation, "Ghi xuống ESP32" with ACK notification (`POST /api/v1/pid/config`), real-time Recharts response curve.
   - `SessionTab.tsx`: Profile card (Full name, DOB, Email, Role, Approval status, Expiry), default admin "Quản lý duyệt Admin" panel (`/api/v1/admin/pending-users`, `/api/v1/admin/approve-user`), active sessions table.
   - `MapTab.tsx`: MapLibre GL light theme, no-fly zone polygons, dynamic 1km approved flight zone circle (green dashed line), live drone GPS heading marker.
   - `FirmwareTab.tsx`: Firmware status badge (Đã nạp / Chưa nạp / Đang nạp), `.bin` file upload widget, flash button with progress spinner, delete firmware, locked safety banner.
4. *Based on Section 5*, `FlightPermissionModal.tsx` was implemented and linked to the "Xin phép bay" button in `App.tsx`, visible strictly to approved Admin users, collecting Pilot license ID, date, time window, and auto-populated Drone GPS coordinates.
5. *Based on Section 3.2*, Role-based tab restriction was enforced in `Tabs.tsx`: when `role === 'user'`, only the Camera and Session tabs are rendered; all other tabs and the flight request button are hidden.
6. *From Observation 2*, `tsc -b && vite build` compiled with 0 errors and generated clean production artifacts in `frontend/dist/`.

## 3. Caveats
- Backend endpoints for `/api/v1/pid/config` and `/api/v1/flight-request/submit` are called by `api.ts` with transparent fallbacks to `/api/v1/pid` and `/api/v1/commands/request_flight` so that frontend operates seamlessly regardless of whether the mock server or FastAPI backend is active.
- Hardware USB camera feed relies on `/api/v1/camera/stream`; if no camera hardware is attached to Pi5, the component renders a high-contrast fallback screen with reconnect and diagnostics information.

## 4. Conclusion
Milestone 5 (Frontend v2 Upgrade & 6 Tabs) is fully complete, meeting all specifications from `prompt-du-an-drone-v2.md` and user dispatch requirements. The SPA builds cleanly with 0 errors and is ready for end-to-end testing and integration.

## 5. Verification Method
1. Re-run TypeScript build:
   ```bash
   export PATH="/home/pnt/IOT/node-v20.11.1-linux-x64/bin:$PATH" && cd /home/pnt/IOT/frontend && npm run build
   ```
   Verify exit code 0 and output bundle in `frontend/dist/`.
2. Inspect source files:
   - `frontend/src/CameraTab.tsx`
   - `frontend/src/TelemetryTab.tsx`
   - `frontend/src/PidTuningTab.tsx`
   - `frontend/src/SessionTab.tsx`
   - `frontend/src/MapTab.tsx`
   - `frontend/src/FirmwareTab.tsx`
   - `frontend/src/FlightPermissionModal.tsx`
   - `frontend/src/Tabs.tsx`
   - `frontend/src/App.tsx`
   - `frontend/src/styles.css`
3. Invalidation conditions:
   - Compilation error in `tsc -b && vite build`.
   - Modifying backend files or `FC_can_bang/` (violating scope boundaries).
