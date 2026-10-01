# Comprehensive Backend, Auth, Safety & Security Survey Report
**Project**: IOT Drone Station v2 (Raspberry Pi 5 + ESP32 + React)  
**Surveyor**: Explorer 2 (Backend, Auth & Security Specialist)  
**Date**: 2026-09-13  
**Status**: Completed  

---

## 1. Executive Summary & Architecture Survey

### 1.1 Workspace vs. Pi5 Deployment State
An exhaustive inspection of the local codebase (`/home/pnt/IOT`) and the physical Raspberry Pi 5 (`192.168.1.118`) revealed two distinct execution environments:
1. **Target Production Environment (`/home/pi5/iot-drone` & `/var/lib/iot-drone`)**:
   - Matches the primary repository layout in `/home/pnt/IOT`.
   - SQLite database: `/var/lib/iot-drone/drone.sqlite3` (WAL mode, ~85MB with >71,000 telemetry samples).
   - Systemd unit: `deploy/iot-drone.service` configured for non-root service user `iot-drone`, group `iot-drone`, with full systemd security sandboxing (`ProtectSystem=strict`, `NoNewPrivileges=true`, `PrivateTmp=true`, `ProtectHome=read-only`, `ReadWritePaths=/var/lib/iot-drone`).
   - Dedicated virtualenv: `/opt/iot-drone/venv` containing Python 3.13.5, FastAPI 0.116.1, and **esptool v5.4.0** already pre-installed.
2. **Auxiliary Prototype Environment (`/opt/drone-web-ui`)**:
   - Currently active as `drone-web-ui.service` on the Pi5.
   - Contains a standalone mock implementation developed during prior prototyping (contains email SMTP OTP utilities and mock PID models, but lacks hardware serial workers, GPS NMEA decoders, and UsbPortCoordinator).
   - Serves on `0.0.0.0:8000` without Caddy TLS termination and runs unhardened as user `pi5`.

### 1.2 Critical Defect Discovered in `backend/app/main.py`
During survey inspection and test collection, a critical syntax error was identified in `backend/app/main.py` (both in the repository and deployed on `/home/pi5/iot-drone/backend/app/main.py`):
- **Observation**:
  - `backend/app/main.py:68`: Literal raw newline escape sequences `\n` were injected by `patch_main.py`:
    ```python
    gps_lost_since: float | None = None\n    global GLOBAL_FLIGHT_PERMISSION\n    flight_permission = GLOBAL_FLIGHT_PERMISSION
    ```
  - `backend/app/main.py:147` & `179`: Invalid Python syntax in FastAPI endpoint decorator:
    ```python
    @app.post("/api/v1/auth/login", response_model=LoginResponse, SetupRequest)
    ```
  - `backend/app/main.py:348-364`: An incomplete loop snippet was pasted directly into the `land()` endpoint body with broken escape characters.
  - `backend/app/main.py:427`: `GLOBAL_FLIGHT_PERMISSION = None\nfrom fastapi import UploadFile, File`
- **Impact**: Pytest fails immediately during collection (`SyntaxError: unexpected character after line continuation character`). The application cannot start in this state until these syntax defects are repaired.

### 1.3 Backend Architecture & Dependencies
The backend is structured under `backend/app/`:
- `config.py`: Central settings loaded from environment (`drone.env`).
- `db.py`: Thread-safe SQLite3 interface using WAL mode and Argon2id password hashing (`time_cost=3, memory_cost=65536, parallelism=2`).
- `models.py`: Pydantic schemas for telemetry, GPS, attitude, PID, commands, and sessions.
- `auth.py`: Session-cookie-based authentication (`drone_session`), sliding-window login rate limiting (`LoginLimiter`: 10 requests / 60s), CSRF token validation (`X-CSRF-Token`), and PyOTP TOTP 2FA.
- `serial_io.py`: Dynamic USB serial arbitrator (`UsbPortCoordinator`), GPS NMEA parser (38400 baud), ESP32 JSONL telemetry/command worker (115200 baud), and `CommandDispatcher` (idempotent 3-try ACK retry).
- `geofence.py`: Shapely geospatial evaluation engine, covering no-fly and restricted polygons from `zones.geojson`.
- `wifi_handler.py`: Provisioning handler receiving Wi-Fi credentials from ESP32 via JSONL and executing `nmcli`.
- `zone_sync.py`: Upstream zone synchronization and hash validation.
- `mod_server.py`: Currently a 15-line stub running on port 9000; requires full implementation per Section 7.

**Dependencies in `backend/requirements.txt`**:
- Current: `fastapi==0.116.1`, `uvicorn[standard]==0.35.0`, `pyserial==3.5`, `pynmea2==1.19.0`, `argon2-cffi==25.1.0`, `pyotp==2.9.0`, `python-multipart==0.0.20`, `shapely==2.1.1`, `httpx==0.28.1`, `mapbox-vector-tile==2.2.0`, `pytest==8.4.1`.
- **Additions required**:
  - `esptool>=5.4.0` (present in Pi5 venv, must be pinned in requirements).
  - `qrcode>=7.4.2` (for rendering TOTP 2FA QR codes to data URIs).
  - `email-validator>=2.2.0` (for strict email format validation).

---

## 2. Database Schema Architecture & Migrations (SQLite3 WAL)

### 2.1 Current Schema Status
The active production database at `/var/lib/iot-drone/drone.sqlite3` currently holds:
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','user')),
    totp_secret TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    created_at TEXT NOT NULL,
    force_change_password INTEGER NOT NULL DEFAULT 0
);
```
The database lacks columns for full name, date of birth, email, requested role, approval status, and first-login tracking.

### 2.2 Target v2 Database Schema
To support all requirements in Sections 3, 4, 7, 8, and 13, the following schema definition and migrations must be applied:

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    full_name TEXT NOT NULL,
    dob TEXT NOT NULL,                         -- ISO format YYYY-MM-DD
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
    requested_role TEXT NOT NULL CHECK(requested_role IN ('admin', 'user')),
    approval_status TEXT NOT NULL DEFAULT 'approved' CHECK(approval_status IN ('pending', 'approved', 'rejected')),
    is_default_admin INTEGER NOT NULL DEFAULT 0,
    first_login_completed INTEGER NOT NULL DEFAULT 1,
    totp_secret TEXT,
    force_change_password INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_approval ON users(approval_status);

-- 2. Sessions Table (Cookie Auth + CSRF)
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf_token TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- 3. Email OTPs Table
CREATE TABLE IF NOT EXISTS email_otps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    otp_code TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK(purpose IN ('register', 'first_login', 'password_reset')),
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    failed_attempts INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_email_otps_lookup ON email_otps(email, purpose, used);

-- 4. Registration Challenges Table (3-Step Registration State)
CREATE TABLE IF NOT EXISTS registration_challenges (
    challenge_id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    dob TEXT NOT NULL,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    requested_role TEXT NOT NULL,
    totp_secret TEXT NOT NULL,
    stage TEXT NOT NULL CHECK(stage IN ('email_otp', 'totp', 'completed')),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reg_challenges_expires ON registration_challenges(expires_at);

-- 5. Firmware Status Table
CREATE TABLE IF NOT EXISTS firmware_status (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    flashed INTEGER NOT NULL DEFAULT 0,
    firmware_version TEXT,
    firmware_hash TEXT,
    flashed_at TEXT,
    flashed_by TEXT
);
INSERT OR IGNORE INTO firmware_status(id, flashed) VALUES (1, 0);

-- 6. Flight Permissions Table (MOD Server Approvals)
CREATE TABLE IF NOT EXISTS flight_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL UNIQUE,
    pilot_name TEXT NOT NULL,
    license_id TEXT NOT NULL,
    drone_id TEXT NOT NULL,
    approved_lat REAL NOT NULL,
    approved_lng REAL NOT NULL,
    radius_m REAL NOT NULL DEFAULT 1000.0,
    flight_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected', 'expired')),
    token TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_flight_permissions_status ON flight_permissions(status);

-- 7. Audit Log Table
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    username TEXT,
    action TEXT NOT NULL,
    detail TEXT,
    remote_addr TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);

-- 8. Existing Telemetry and Map Sync Tables
CREATE TABLE IF NOT EXISTS telemetry_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_telemetry_created_at ON telemetry_samples(created_at);

CREATE TABLE IF NOT EXISTS map_sync (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    source_url TEXT,
    fetched_at TEXT,
    checksum TEXT,
    feature_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'missing'
);
INSERT OR IGNORE INTO map_sync(id, status) VALUES (1, 'missing');
```

### 2.3 Migration Script Strategy (`backend/migrate.py`)
To ensure zero data loss on existing Pi5 installations, a safe migration function checks column existence via `PRAGMA table_info(users)` and adds missing columns dynamically, followed by seeding the default `pi5` account if absent:
```python
def migrate_database(conn: sqlite3.Connection):
    # Alter users table
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users);")
    cols = {row["name"] for row in cursor.fetchall()}
    
    if "full_name" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT NOT NULL DEFAULT 'System Admin';")
    if "dob" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN dob TEXT NOT NULL DEFAULT '2000-01-01';")
    if "email" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT;")
    if "requested_role" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN requested_role TEXT NOT NULL DEFAULT 'admin';")
    if "approval_status" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'approved';")
    if "is_default_admin" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN is_default_admin INTEGER NOT NULL DEFAULT 0;")
    if "first_login_completed" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN first_login_completed INTEGER NOT NULL DEFAULT 1;")
        
    # Ensure default 'pi5' admin exists
    cursor.execute("SELECT id, is_default_admin, first_login_completed FROM users WHERE username='pi5';")
    row = cursor.fetchone()
    if not row:
        # Create default pi5 user with password '123456'
        now = datetime.now(timezone.utc).isoformat()
        ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
        cursor.execute(
            """INSERT INTO users (username, full_name, dob, email, password_hash, role, requested_role,
                                  approval_status, is_default_admin, first_login_completed, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?)""",
            ('pi5', 'Default Pi5 Admin', '2000-01-01', 'pi5-unconfigured@drone.local', ph.hash('123456'),
             'admin', 'admin', 'approved', now)
        )
    conn.commit()
```

---

## 3. Authentication, Role-Based Access Control & Onboarding Flows

### 3.1 Three-Step User Registration Flow
Per Spec Section 3.1, registration requires Full Name, Date of Birth, Email, Password, and Requested Role (`user` or `admin`), followed by Email OTP and PyOTP (TOTP 2FA).

```
[Client]                                            [Pi5 Backend API]                                    [Email / Journal]
   |                                                        |                                                    |
   |--- 1. POST /api/v1/auth/register --------------------->|                                                    |
   |    {full_name, dob, email, password, requested_role}   | Validate fields, hash pwd                          |
   |                                                        | Generate 6-digit OTP                               |
   |                                                        | Store in registration_challenges                   |
   |                                                        |---------------- Send OTP email ------------------->|
   |<-- Return {challenge_id, step: "email_otp"} -----------|                                                    |
   |                                                        |                                                    |
   |--- 2. POST /api/v1/auth/register/verify-otp ---------->|                                                    |
   |    {challenge_id, otp_code}                            | Verify OTP & expiry                                |
   |                                                        | Generate TOTP secret (pyotp.random_base32())       |
   |                                                        | Generate QR code Data URL (qrcode lib)             |
   |<-- Return {challenge_id, totp_secret, qr_code, step}---|                                                    |
   |                                                        |                                                    |
   |--- 3. POST /api/v1/auth/register/verify-totp --------->|                                                    |
   |    {challenge_id, totp_code}                           | Verify TOTP token                                  |
   |                                                        | Commit user to DB:                                 |
   |                                                        | - If role=user: active immediately (approved)      |
   |                                                        | - If role=admin: status=pending, role=user         |
   |<-- Return {success: true, role, approval_status} ------|                                                    |
```

### 3.2 Role and Approval State Machine
Per Spec Section 3.2:
- **User Role**:
  - `role = 'user'`, `approval_status = 'approved'`.
  - Active immediately upon completing registration.
  - Access restriction: **Can only view the Camera tab** (`/api/v1/camera/status`, WebRTC/video stream). All telemetry, PID tuning, serial monitor, maps, and flight commands return `403 Forbidden`.
- **Admin Role (Self-Registered)**:
  - `role = 'user'` (effective role), `requested_role = 'admin'`, `approval_status = 'pending'`.
  - **While pending**: Operates with identical permissions to `user` (Camera tab only).
  - **Upon approval by default admin**: `approval_status` transitions to `'approved'`, and `role` updates to `'admin'`. Full administrative privileges are unlocked.
  - **Upon rejection**: `approval_status` transitions to `'rejected'`. Remains restricted or disabled.

### 3.3 Default Admin (`pi5`) First-Login Enforcement
Per Spec Section 3.3, 11, and 12.1 item 5:
- The default admin username is `pi5`, initial password `123456`, flagged with `is_default_admin = 1` and `first_login_completed = 0`.
- **Interception Gate**:
  The authentication dependency `session_user` checks:
  ```python
  if user["is_default_admin"] == 1 and user["first_login_completed"] == 0:
      # If request path is NOT in allowed setup paths, block execution!
      allowed_endpoints = {
          "/api/v1/auth/me",
          "/api/v1/auth/logout",
          "/api/v1/auth/first-login/request-otp",
          "/api/v1/auth/first-login/confirm-otp"
      }
      if request.url.path not in allowed_endpoints:
          raise HTTPException(
              status_code=status.HTTP_428_PRECONDITION_REQUIRED,
              detail="Admin mặc định bắt buộc phải cập nhật email và xác nhận OTP trước khi truy cập hệ thống."
          )
  ```
- **First-Login Workflow**:
  1. Login with `pi5` / `123456` succeeds, sets session cookie, returns `require_first_login_setup: true`.
  2. Frontend locks UI into a dedicated mandatory modal dialog.
  3. Admin enters new official email -> Calls `POST /api/v1/auth/first-login/request-otp`.
  4. Backend generates 6-digit numeric OTP, logs to `email_otps` table, and dispatches email via SMTP (or fallback log).
  5. Admin inputs OTP and optionally a strong replacement password -> Calls `POST /api/v1/auth/first-login/confirm-otp`.
  6. Backend validates OTP:
     - Updates `users`: `email = new_email`, `first_login_completed = 1`, updates password hash.
     - Logs `default_admin_first_login_completed` in `audit_log`.
     - Full administrative access is unlocked.

### 3.4 Email OTP Engine (SMTP & Offline Fallback)
To ensure reliable operation in offline LAN drone field environments:
- **SMTP Mode**: When `SMTP_HOST`, `SMTP_USER`, and `SMTP_PASS` are defined in environment variables, OTP is delivered via TLS to the recipient email.
- **Offline / Dev Fallback**: If SMTP is unreachable or unconfigured, the system logs the OTP at `WARNING` level to the systemd journal (`journalctl -u iot-drone`) and writes an audit event `otp_emitted_offline`. If `DEV_MODE=true`, it may also be displayed in backend logs for verification.
- **Brute-Force Safeguard**:
  - OTP expires strictly after 10 minutes.
  - Rate-limited to max 3 requests per 15 minutes per IP/email.
  - Maximum 5 failed verification attempts per OTP; exceeding burns the OTP immediately.

---

## 4. ESP32 Firmware Flashing Pipeline on Pi5

### 4.1 Firmware Storage & Artifact Management
- Source directory: `/home/pnt/IOT/FC_can_bang`.
- Pre-compiled production binaries located in `/home/pnt/IOT/FC_can_bang/build/esp32.esp32.esp32/`:
  - `FC_can_bang.ino.merged.bin`: 4,194,304 bytes (complete 4MB image mapped at offset `0x0`).
  - Individual components: `bootloader.bin` (`0x1000`), `partitions.bin` (`0x8000`), `boot_app0.bin` (`0xe000`), `FC_can_bang.ino.bin` (`0x10000`).
  - Copy present on Pi5: `/home/pi5/FC_can_bang.ino.merged.bin`.
- Target runtime storage on Pi5:
  `/var/lib/iot-drone/firmware/current.bin` and `/var/lib/iot-drone/firmware/backup.bin` (for automatic rollback if flashing fails).

### 4.2 Flashing Execution & Serial Arbitration
Serial flashing via `esptool` requires exclusive physical control of the serial adapter (e.g. `/dev/ttyUSB0` or `/dev/ttyUSB1`). Currently, `esp_worker` holds the serial port open continuously in a background thread.
**Required Flashing Procedure**:
1. **Acquire Flashing Lock**:
   Reject concurrent flashing requests with `409 Conflict`.
2. **Serial Port Suspension**:
   - Query `coordinator.get_device_for_role("esp")` to get the active serial path.
   - Signal `esp_worker.stop()`, join thread, and close the serial port handle.
   - Call `coordinator.release_device_for_role("esp")` so the OS file descriptor is completely released.
3. **Execute `esptool`**:
   Run `esptool` using `/opt/iot-drone/venv/bin/esptool` via `asyncio.create_subprocess_exec`:
   ```bash
   /opt/iot-drone/venv/bin/esptool \
       --chip esp32 \
       --port /dev/ttyUSB0 \
       --baud 460800 \
       --before default_reset \
       --after hard_reset \
       write_flash -z --flash_mode dio --flash_freq 80m --flash_size 4MB \
       0x0 /var/lib/iot-drone/firmware/current.bin
   ```
4. **Post-Flash Restoration**:
   - On success (exit code 0):
     - Update database `firmware_status`: `flashed = 1`, `flashed_at = now()`, `firmware_hash = sha256`.
     - Write flag file `/var/lib/iot-drone/firmware_flashed.flag`.
     - Restart `esp_worker.start()`.
     - Record `firmware_flash_success` in `audit_log`.
   - On failure:
     - Keep `firmware_status.flashed = 0`.
     - Reconnect `esp_worker.start()`.
     - Record `firmware_flash_failed` in `audit_log`.
     - Return detailed error log to client.

### 4.3 Drone Control Lockout Mechanism
Per Spec Section 4, 11, and 12.1 item 6:
All drone control, PID modification, and flight capabilities are strictly blocked until firmware is successfully flashed.
- **Backend Dependency**:
  ```python
  def require_firmware_flashed():
      with db.connect() as conn:
          row = conn.execute("SELECT flashed FROM firmware_status WHERE id=1").fetchone()
      flag_file = settings.data_dir / "firmware_flashed.flag"
      if not (row and row["flashed"] and flag_file.exists()):
          raise HTTPException(
              status_code=status.HTTP_428_PRECONDITION_REQUIRED,
              detail="Chưa nạp firmware cho ESP32. Toàn bộ tính năng điều khiển bị khóa cho đến khi hoàn thành nạp FW."
          )
  ```
- **Protected Endpoints**:
  - `/api/v1/commands/*` (`land`, `request_flight`)
  - `/api/v1/drone/pid` (writing or modifying PID parameters)
  - Preflight check reports `"firmware_flashed": false`, forcing overall preflight status to `"ready": false`.
- **Frontend Navigation Gate**:
  If `/api/v1/firmware/status` returns `flashed: false`, the React application redirects admin to Tab 6 (Quản lý FW) and disables tabs 2, 3, and 5.

---

## 5. ARM Locking Fail-Safe Mechanism & MOD Server Integration

### 5.1 Architecture Overview
The safety architecture guarantees that a drone cannot arm or remain in flight unless strict, multi-layered authorization and physical constraints are met.

```
       +-------------------------------------------------------------+
       |                  MOD Server (Independent)                   |
       |  - Approves flight request for pilot, license, drone ID     |
       |  - Grants polygon/radius (1000m) & [start_time, end_time]   |
       +-------------------------------------------------------------+
                                      |
                           HTTP POST / REST (JSON)
                                      v
       +-------------------------------------------------------------+
       |               Raspberry Pi 5 GCS (Backend)                  |
       |                                                             |
       |  safety_command_loop (10 Hz Continuous Evaluation):         |
       |  1. Flight permission valid & approved?                     |
       |  2. Current time within [start_time, end_time]?             |
       |  3. GPS fix valid, not stale (<5s), HDOP < 5.0?             |
       |  4. Distance to approved center <= 1000 m?                  |
       |  5. Outside prohibited/restricted geofence zones?           |
       |                                                             |
       |  FAIL-SAFE RULE: Missing/invalid data -> ARM LOCKED!        |
       +-------------------------------------------------------------+
                                      |
                      Serial JSONL (115200 baud)
                                      v
       +-------------------------------------------------------------+
       |                   ESP32 Flight Controller                   |
       |  FC_can_bang.ino lines 201-205:                             |
       |  if (!flight_permission) { status_arm = 0; }                |
       |  Motors cut/locked; arming switch disabled.                 |
       +-------------------------------------------------------------+
```

### 5.2 MOD Server Flight Permission Contract
- **MOD Server Spec (Section 7)**:
  Runs on an independent host (accessible from any network).
  - Endpoint `POST /api/v1/mod/flight-request`:
    Payload: `{pilot_name, license_id, drone_id, lat, lng, flight_date, start_time, end_time}`.
  - Endpoint `POST /api/v1/mod/requests/{id}/approve`:
    Admin approves -> Returns token, approved center `(lat, lng)`, `radius_m = 1000.0`, `valid_from`, `valid_until`.
  - Automatic Expiration:
    The approved flight zone is only active during the registered window. Hết giờ -> closes automatically and returns to prohibited state.

### 5.3 Backend ARM Validation Engine
Implemented in `backend/app/safety.py` / `main.py`:
```python
def evaluate_arm_safety(gps: GpsFix, permission: FlightPermission | None, geofence_state: GeofenceState) -> tuple[bool, str]:
    now = datetime.now(timezone.utc)
    
    # 1. Check MOD permission existence & approval status
    if not permission or permission.status != "approved":
        return False, "NO_MOD_FLIGHT_PERMISSION"
        
    # 2. Check time window
    start_dt = datetime.fromisoformat(permission.start_time)
    end_dt = datetime.fromisoformat(permission.end_time)
    if now < start_dt:
        return False, f"FLIGHT_WINDOW_NOT_OPEN (starts at {permission.start_time})"
    if now > end_dt:
        return False, f"FLIGHT_WINDOW_EXPIRED (expired at {permission.end_time})"
        
    # 3. Check GPS fix health
    if not gps.valid or gps.stale or gps.latitude is None or gps.longitude is None:
        return False, "GPS_INVALID_OR_STALE"
    if gps.hdop is not None and gps.hdop > 5.0:
        return False, f"GPS_HDOP_TOO_HIGH ({gps.hdop})"
    if gps.satellites is not None and gps.satellites < 4:
        return False, f"INSUFFICIENT_SATELLITES ({gps.satellites})"
        
    # 4. Check distance constraint (strict <= 1000m / 1km radius)
    dist_m = haversine_m(gps.longitude, gps.latitude, permission.approved_lng, permission.approved_lat)
    if dist_m > permission.radius_m:
        return False, f"OUTSIDE_APPROVED_GEOFENCE ({dist_m:.1f}m > {permission.radius_m}m)"
        
    # 5. Check hard static geofence
    if geofence_state.status == "breach":
        return False, f"STATIC_GEOFENCE_BREACH ({geofence_state.zone_name})"
        
    return True, "ARM_PERMITTED"
```

### 5.4 Continuous Safety Loop & Serial Protocol
In `safety_command_loop()` running at 10Hz:
- Evaluate `permitted, reason = evaluate_arm_safety(frame.gps, active_permission, frame.geofence)`.
- **If `permitted == False`**:
  - Broadcast serial lock to ESP32:
    `{"type": "permission", "granted": false, "reason": reason}`
  - If drone is reported as `armed == True` while permission is denied:
    Trigger emergency failsafe:
    `await command_dispatcher.land(reason="ARM_LOCK_VIOLATION")`
    Audit log: `arm_lock_failsafe_triggered`.
- **If `permitted == True`**:
  - Send serial permission heartbeat to ESP32:
    `{"type": "permission", "granted": true, "remaining_seconds": int((end_dt - now).total_seconds())}`
- **Firmware Safety**:
  As verified in `FC_can_bang/FC_can_bang.ino` lines 201-205:
  ```cpp
  if (!flight_permission) {
    status_arm = 0;
  }
  ```
- **Strict Constraint**:
  `ENABLE_REAL_FLIGHT_COMMANDS=false` must remain `false` in configuration. Pi5 never sends raw motor commands directly.

---

## 6. Security Hardening Roadmap & Audit Criteria (Section 13)

### 6.1 Vulnerability Assessment Matrix

| Item | Category | Current State on Pi5 | Risk Level | Target Hardened State |
|---|---|---|---|---|
| **13.1** | Default SSH Password | User `pi5` has password `123456`. `PasswordAuthentication no` is set in sshd, but sudo uses password. | **HIGH** | Change password to cryptographically strong string; enforce SSH Ed25519 key authentication only. |
| **13.1** | Root Login | `PermitRootLogin` is commented out (defaults to `prohibit-password`). | **MEDIUM** | Explicitly configure `PermitRootLogin no`. |
| **13.1** | Fail2ban | Not installed on Pi5. | **HIGH** | Install Fail2ban; configure jails for SSH (port 22) and Web API login failures. |
| **13.2 #1** | Firewall & Exposed Ports | Ports `8000` (uvicorn) and `9000` (mod server) listen on `0.0.0.0`; rpcbind (111), VNC (5900), xrdp (3389) active. | **HIGH** | Bind uvicorn strictly to `127.0.0.1:8000`; enforce UFW: allow only `443/tcp+udp`, `22/tcp`, `5353/udp` from LAN. |
| **13.2 #2** | Web Auth & Rate Limiting | `LoginLimiter` protects login; missing rate limiting on OTP verification and register endpoints. | **MEDIUM** | Implement IP + account rate limiting on `/register`, `/verify-otp`, `/first-login/*`. |
| **13.2 #2** | Cookie Security | `drone_session` cookie has `HttpOnly=True`, `SameSite=strict`. `Secure` flag depends on `COOKIE_SECURE`. | **LOW** | Ensure `COOKIE_SECURE=true` in `/etc/iot-drone/drone.env` for HTTPS. |
| **13.2 #3** | CSRF / XSS / SQLi | CSRF tokens enforced on mutating endpoints; SQL parameterized. Inputs lack length/type validation in some endpoints. | **LOW** | Add Pydantic sanitization and regex validation on pilot names, license IDs, and text fields. |
| **13.2 #4** | Serial Command Injection | Serial JSONL commands lack message authentication token; arbitrary USB adapter could theoretically send JSON lines. | **MEDIUM** | Implement command token / HMAC authentication on serial frames between Pi5 and ESP32. |
| **13.2 #5** | GPS Spoofing Detection | Parser accepts NMEA without kinematic velocity / jump verification. | **MEDIUM** | Implement kinematic delta check: flag coordinate jump > 50 m/s; compare GPS altitude against LiDAR altitude. |
| **13.2 #6** | Public MOD Server Security | `mod_server.py` is an unsecured prototype on port 9000. | **HIGH** | Isolate MOD server to separate PC; require TLS, strong authentication, and rate limiting. |
| **13.2 #7** | Firmware Integrity | Flashing accepts uploaded files without SHA256 / signature verification. | **MEDIUM** | Enforce firmware SHA256 checksum whitelist before executing `esptool write_flash`. |
| **13.2 #9** | Audit Logging | `audit_log` table exists in DB, but does not cover all administrative and safety events. | **LOW** | Expand audit logging to cover all 14 sensitive event categories. |

### 6.2 Hardening Implementation Specifications

#### A. Host & SSH Hardening
1. Update `/etc/ssh/sshd_config.d/01-drone-hardened.conf`:
   ```text
   PasswordAuthentication no
   PermitRootLogin no
   PubkeyAuthentication yes
   AuthorizedKeysFile .ssh/authorized_keys
   KbdInteractiveAuthentication no
   X11Forwarding no
   MaxAuthTries 3
   ```
2. User `pi5` sudo password change:
   Generate strong random 24-character password, stored securely or configure sudoers for specific deployment commands.

#### B. Fail2ban Setup
1. Install package: `apt-get install -y fail2ban`
2. Create `/etc/fail2ban/jail.d/drone.local`:
   ```ini
   [sshd]
   enabled = true
   port = 22
   filter = sshd
   maxretry = 3
   findtime = 600
   bantime = 3600

   [iot-drone-login]
   enabled = true
   port = 443,8000
   filter = iot-drone-auth
   logpath = /var/log/iot-drone/audit.log
   maxretry = 5
   findtime = 300
   bantime = 1800
   ```
3. Create filter `/etc/fail2ban/filter.d/iot-drone-auth.conf`:
   ```ini
   [Definition]
   failregex = ^.*login_failed.*remote_addr=<HOST>.*$
   ignoreregex =
   ```

#### C. Firewall & Port Enforcement (UFW)
```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow from 192.168.1.0/24 to any port 22 proto tcp comment 'SSH LAN'
ufw allow from 192.168.1.0/24 to any port 443 proto tcp comment 'Drone HTTPS LAN'
ufw allow from 192.168.1.0/24 to any port 443 proto udp comment 'Drone HTTP3 LAN'
ufw allow from 192.168.1.0/24 to any port 5353 proto udp comment 'mDNS LAN'
ufw --force enable
```
Ensure Uvicorn binds strictly to `127.0.0.1:8000` via `deploy/iot-drone.service`:
`ExecStart=/opt/iot-drone/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers`

#### D. Serial Command Authentication
To prevent malicious or accidental command injection via secondary USB serial adapters:
- Generate a shared secret key `SERIAL_SHARED_KEY` in `/etc/iot-drone/drone.env`.
- On high-consequence serial commands (e.g. `permission`, `LAND`, `LOCK_ARM`):
  Include an HMAC token:
  ```json
  {
    "version": 1,
    "type": "command",
    "command": "LAND",
    "id": "c1a9...",
    "timestamp": 1789381200,
    "auth": "a3f8c..."
  }
  ```

#### E. GPS Spoofing & Anomalous Jump Detection
Add an algorithmic spoofing filter to `backend/app/serial_io.py`:
- Calculate Haversine distance between current fix and last valid fix.
- Delta time `dt = now - last_time`.
- If `dt > 0.1` and `dist_m / dt > 50.0` (meters per second, exceeding drone flight envelope):
  Flag fix as anomalous: `fix.valid = False`, `fix.spoofed = True`.
- LiDAR Cross-Check:
  If `frame.attitude.lidar_altitude_m` is available (e.g. 2.0m on ground) but GPS altitude suddenly indicates 500m:
  Flag as vertical altitude spoofing -> reject fix.

#### F. Audit Logging Comprehensive Coverage
The `audit_log` table must record all of the following events:
1. `user_register_started`, `user_register_completed`
2. `email_otp_sent`, `email_otp_verified`, `email_otp_failed`
3. `totp_verified`, `totp_failed`
4. `default_admin_email_updated`, `password_changed`
5. `admin_approved_user`, `admin_rejected_user`
6. `firmware_flash_started`, `firmware_flash_success`, `firmware_flash_failed`, `firmware_deleted`
7. `flight_permission_requested`, `flight_permission_approved`, `flight_permission_expired`
8. `arm_lock_violation`, `automatic_land_triggered`, `manual_land_command`
9. `pid_updated`
10. `geofence_sync`

---

## 7. Actionable Implementation Recommendations

1. **Repair `backend/app/main.py` Immediately**:
   - Revert malformed line continuation characters on line 68, line 427, and lines 348-364.
   - Fix response model decorators on lines 147 and 179 (`response_model=LoginResponse`).
2. **Execute Database Migrations**:
   - Run updated `migrate.py` to upgrade `/var/lib/iot-drone/drone.sqlite3` and create required v2 tables (`users`, `email_otps`, `registration_challenges`, `firmware_status`, `flight_permissions`).
   - Ensure default `pi5` user is seeded with `is_default_admin=1` and `first_login_completed=0`.
3. **Consolidate Services on Pi5**:
   - Stop and disable rogue prototype `drone-web-ui.service` running unauthenticated on port 8000.
   - Deploy `deploy/iot-drone.service` to run sandboxed as user `iot-drone` bound to `127.0.0.1:8000`, with Caddy serving HTTPS on port 443.
4. **Implement Auth Endpoints**:
   - Build 3-step registration router (`/api/v1/auth/register`, `/verify-otp`, `/verify-totp`).
   - Implement `pi5` first-login gate (`/api/v1/auth/first-login/*`).
   - Implement admin approval management (`/api/v1/admin/pending-users`, `/users/{id}/approve`, `/users/{id}/reject`).
5. **Implement Firmware Flasher Service**:
   - Implement `POST /api/v1/firmware/flash` using `/opt/iot-drone/venv/bin/esptool` with port unbinding and post-flash worker restart.
   - Enforce `require_firmware_flashed` dependency across all control endpoints.
6. **Implement ARM Locking & MOD Protocol**:
   - Implement standalone MOD server on port 9000 or external host with approval and zone expiration logic.
   - Connect Pi5 `safety_command_loop` to active MOD permissions with strict fail-safe rules.
