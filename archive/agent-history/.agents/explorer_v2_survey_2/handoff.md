# Handoff Report — Explorer 2 (Backend, Auth & Security Specialist)

## 1. Observation
1. **Critical Syntax Errors in `backend/app/main.py`**:
   - `backend/app/main.py:68`:
     `gps_lost_since: float | None = None\n    global GLOBAL_FLIGHT_PERMISSION\n    flight_permission = GLOBAL_FLIGHT_PERMISSION`
   - `backend/app/main.py:147` & `179`:
     `@app.post("/api/v1/auth/login", response_model=LoginResponse, SetupRequest)` and `@app.get("/api/v1/auth/me", response_model=LoginResponse, SetupRequest)` contain invalid Python tuple syntax in decorators.
   - `backend/app/main.py:348-364`: Contains fragmented indentation and raw `\n` characters embedded in the `land()` endpoint body.
   - Running test collection via `PYTHONPATH=. /opt/iot-drone/venv/bin/pytest -q` on Pi5 produces verbatim error:
     `File "/home/pi5/iot-drone/backend/app/main.py", line 68`
     `SyntaxError: unexpected character after line continuation character`
2. **Current Production Database on Pi5**:
   - `/var/lib/iot-drone/drone.sqlite3` contains tables: `users`, `sessions`, `audit_log`, `telemetry_samples` (>71,500 records), `map_sync`, `sqlite_stat1`.
   - Inspection of `PRAGMA table_info(users)` confirms columns are: `['id', 'username', 'password_hash', 'role', 'totp_secret', 'enabled', 'failed_attempts', 'locked_until', 'created_at', 'force_change_password']`.
   - Missing fields: `full_name`, `dob`, `email`, `requested_role`, `approval_status`, `is_default_admin`, `first_login_completed`.
   - Seeded user is `admin`, not `pi5`.
3. **Firmware Tooling & Artifacts**:
   - `esptool v5.4.0` is already installed on Pi5 at `/opt/iot-drone/venv/bin/esptool`.
   - Merged 4MB binary exists at `/home/pi5/FC_can_bang.ino.merged.bin` and in repo at `/home/pnt/IOT/FC_can_bang/build/esp32.esp32.esp32/FC_can_bang.ino.merged.bin`.
   - Flashing requires offset `0x0` for merged binary, or individual offsets: `0x1000 bootloader.bin`, `0x8000 partitions.bin`, `0xe000 boot_app0.bin`, `0x10000 FC_can_bang.ino.bin`.
4. **Hardware ARM Failsafe in Firmware**:
   - `FC_can_bang/FC_can_bang.ino:201-205` directly implements:
     ```cpp
     // FAILSAFE: Lock ARM if permission not granted
     if (!flight_permission) {
       status_arm = 0;
     }
     ```
   - `FC_can_bang/display.ino:31-33` handles serial JSON:
     ```cpp
     else if (type == "permission") {
       flight_permission = doc["granted"] | false;
     }
     ```
5. **Host Security Posture on Pi5 (`192.168.1.118`)**:
   - SSH key auth works via `/home/pi5/.ssh/authorized_keys`; `/etc/ssh/sshd_config` has `PasswordAuthentication no`.
   - `dpkg -l fail2ban` returns `NOT_INSTALLED`.
   - `ss -tulpn` shows `uvicorn` listening on `0.0.0.0:8000` under process PID 2968 (`drone-web-ui.service`), and `python` listening on `0.0.0.0:9000` (`mod_server.py`).

## 2. Logic Chain
1. Based on Observation 1, the backend codebase cannot execute unit tests or run under uvicorn without repairing the syntax errors caused by `patch_main.py`. The decorators and loop blocks must be restored and cleanly modularized before feature development.
2. Based on Observation 2, `backend/migrate.py` must be upgraded to dynamically add missing user fields, create `email_otps`, `registration_challenges`, `firmware_status`, and `flight_permissions` tables, and seed `pi5` with `is_default_admin=1` and `first_login_completed=0`.
3. Based on Observation 3, the firmware flashing pipeline on Pi5 has all binary and tooling prerequisites met. However, `esp_worker` in `backend/app/serial_io.py` must release its serial port lease before `esptool` can access the USB device without serial resource contention.
4. Based on Observation 4, the ESP32 firmware already has the hardware ARM locking latch in place (`status_arm = 0`). The Pi5 backend's role is to run a 10Hz continuous evaluation loop (`safety_command_loop`) checking MOD approval, 1000m radius distance, time window, and GPS validity, transmitting `{"type": "permission", "granted": false}` whenever any constraint fails.
5. Based on Observation 5, Pi5 is currently running an unhardened prototype service (`drone-web-ui.service`) binding directly to `0.0.0.0:8000`. Deploying `deploy/iot-drone.service` will bind Uvicorn to `127.0.0.1:8000`, route through Caddy HTTPS on port 443 with sandbox protections, and allow configuring UFW to restrict all other non-essential ports.

## 3. Caveats
- Sudo password on Pi5: Sudo password attempt with `123456` was rejected, indicating the system user `pi5` password was changed or differs from documentation. However, SSH Ed25519 key login is fully operational.
- MOD Server Location: Spec Section 7 states MOD server runs on an independent PC accessible from any network. For local simulation and testing, running `mod_server.py` on a distinct port/process is acceptable, but production requires independent hosting.
- `ENABLE_REAL_FLIGHT_COMMANDS` was confirmed to be `false` in config and `.env.example`, strictly adhering to safety rules.

## 4. Conclusion
The Pi5 backend architecture is sound and well-structured, but requires immediate syntax repair in `main.py`, database schema migrations, and replacement of the active prototype service on Pi5 with the sandboxed `iot-drone.service`.
The detailed survey report has been compiled and saved to `/home/pnt/IOT/.agents/explorer_v2_survey_2/report.md` covering:
1. Comprehensive Database Schema and migration definitions.
2. 3-step User Registration, Email OTP, PyOTP TOTP 2FA, and Default Admin First-Login Gate.
3. ESP32 Firmware Flashing Pipeline with exclusive serial arbitration and Control Lockout.
4. Fail-Safe ARM Locking Logic with MOD Flight Permission validation and 1000m geofence checks.
5. Security Hardening Matrix covering SSH, Fail2ban, UFW, cookie security, serial auth, and audit logging.

## 5. Verification Method
1. **Verify Syntax and Collection**:
   Fix lines in `backend/app/main.py` and run:
   ```bash
   cd /home/pnt/IOT/backend && PYTHONPATH=. pytest -q --collect-only
   ```
   Invalidation condition: Any syntax error or import failure during collection.
2. **Verify Database Migration**:
   Run:
   ```bash
   cd /home/pnt/IOT/backend && python3 -c "from app.db import db; db.initialize()"
   ```
   Inspect `/home/pnt/IOT/backend/data/drone.sqlite3` schema using `sqlite3` to confirm `full_name`, `dob`, `email`, `requested_role`, `approval_status`, `is_default_admin`, and `first_login_completed` exist.
3. **Verify Pi5 Tools**:
   Run via SSH:
   ```bash
   ssh pi5@192.168.1.118 "/opt/iot-drone/venv/bin/esptool version"
   ```
   Expect output: `esptool v5.4.0`.
