## 2026-09-13T13:04:04Z

You are the Frontend Worker for Milestone 5 (M5: Frontend v2 Upgrade & 6 Tabs).
Your working directory: /home/pnt/IOT/.agents/worker_m5_frontend_r2
User request record: /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (read section ## 2026-09-13T09:30:16Z)
Specification file: /home/pnt/IOT/prompt-du-an-drone-v2.md (pay special attention to Sections 1, 5, 6, 8, 9, 10, 11)
Project documentation: /home/pnt/IOT/PROJECT.md
Survey findings: /home/pnt/IOT/.agents/explorer_v2_survey_3/report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Boundaries:
You have exclusive write ownership of `frontend/` (primarily `frontend/src/`). DO NOT modify `backend/` or `FC_can_bang/`.

Your Mission:
Upgrade the React 19 single-page application in `frontend/` to version 2:
1. Unified Blue-White Theme System:
   - Replace the dark cyberpunk color palette in `frontend/src/styles.css` with a clean, high-contrast Blue-White aviation GCS design system:
     - Background: `#f4f7fb` / `#ffffff`
     - Panels / Cards: `#ffffff` with subtle borders (`#e2e8f0`) and soft elevation.
     - Brand Blue: Primary `#0066cc`, Hover `#0052a3`, Light tint `#ebf3fc`.
     - Accents: Status green `#16a34a`, Warning amber `#d97706`, Alert red `#dc2626`.
     - High contrast slate text: `#0f172a` / `#475569`.
   - Ensure the theme is clean, modern, and consistent across all pages and modals.
2. 6 Dedicated Functional Tabs (Section 6):
   Organize the main view into 6 distinct, accessible tabs:
   - Tab 1: **Camera** (`CameraTab.tsx`):
     - USB live video stream display (`/api/v1/camera/stream` with fallback/error handling).
     - Snapshot capture button and stream resolution/FPS indicator.
   - Tab 2: **Telemetry & 3D** (`TelemetryTab.tsx`):
     - Three.js / R3F interactive 3D drone attitude model showing Roll, Pitch, Yaw.
     - Telemetry gauges: Roll, Pitch, Yaw, Heading, Battery.
     - Prominent **LiDAR Altitude display** (`lidar_altitude_m` / `Altitude_kalman`) in meters.
   - Tab 3: **PID Tuning** (`PidTuningTab.tsx`):
     - Upgrade from read-only to full interactive read/write serial control.
     - Reads current Kp, Ki, Kd parameters from backend (`GET /api/v1/pid/config`).
     - Input fields with validation to adjust Roll/Pitch/Yaw PID gains.
     - "Ghi xuống ESP32" (Write to ESP32) button with ACK notification (`POST /api/v1/pid/config`).
     - Real-time Recharts response curve.
   - Tab 4: **Current Session** (`SessionTab.tsx`):
     - Displays logged-in user profile: Full Name, DOB, Email, Role (User / Admin), Approval Status, Session Expiry.
     - Logout button.
     - For default admin: "Quản lý duyệt Admin" (Approve pending admin registrations) panel.
   - Tab 5: **Map** (`MapTab.tsx`):
     - MapLibre GL map with offline PMTiles/vector support.
     - Drone live GPS position marker with heading indicator.
     - Display no-fly zones (prohibited / restricted polygons from backend).
     - Display dynamic 1km approved flight zone (green dashed circle) when flight permission is active.
   - Tab 6: **Firmware Management** (`FirmwareTab.tsx`):
     - Firmware status badge (Đã nạp / Chưa nạp / Đang nạp).
     - File upload widget for `.bin` firmware file (`POST /api/v1/firmware/upload`).
     - "Nạp Firmware vào ESP32" (Flash Firmware) button (`POST /api/v1/firmware/flash`) with progress spinner.
     - Delete firmware button (`DELETE /api/v1/firmware/{filename}`).
     - Prominent warning banner: Flight control features are strictly locked until firmware is verified flashed!
3. Header & Flight Permission Request Modal (Section 5):
   - Header displaying Drone ID, GPS status, ARM status (Khóa / Sẵn sàng).
   - **"Xin phép bay" (Request Flight Permission) Button**:
     - Visible only to approved Admin users.
     - Opens modal dialog:
       * Full name (prefilled from session).
       * Pilot license ID (`license_id`).
       * Flight date (`flight_date`).
       * Time window (`time_from` to `time_to`).
       * Current Drone GPS coordinates (auto-populated from telemetry).
     - Submits to backend `/api/v1/flight-request/submit` -> forwards to MOD server.
     - Displays status toast / badge ("Chờ Bộ Quốc phòng duyệt" / "Đã được duyệt" / "Bị từ chối").
4. Role-Based Tab Restriction:
   - When logged-in user has role `user`: ONLY the Camera tab (and Session info) is visible/accessible. Tabs 2, 3, 5, 6 and the "Xin phép bay" button are hidden.
5. Compilation & Build Verification:
   - Run `export PATH="/home/pnt/IOT/node-v20.11.1-linux-x64/bin:$PATH" && cd /home/pnt/IOT/frontend && npm run build`.
   - Ensure exit code 0, 0 TypeScript errors, bundle cleanly produced in `frontend/dist/`.
