## 2026-09-13T09:32:12Z

Conduct a comprehensive, read-only survey of the Pi5 backend in `/home/pnt/IOT/backend`, systemd services, database schemas, security posture, and safety logic.
1. Survey the backend architecture (`backend/app`, database, schemas, routers, dependencies in `requirements.txt` or `pyproject.toml`).
2. Examine the current auth system and database models (SQLite3 WAL):
   - How are users and roles structured?
   - How to implement user registration with Full Name, DOB, Email, Password, Requested Role (User/Admin)?
   - How email OTP is/should be sent and verified?
   - How PyOTP (TOTP 2FA) is currently used and how to integrate it with the new flow?
   - How to enforce the first-login rule for default admin 'pi5' (mandatory email update + OTP confirmation before any other access)?
   - How the pending admin approval workflow works (User active immediately for camera only; Admin pending approval acts as User until approved by default admin)?
3. Investigate the firmware flashing pipeline on Pi5:
   - Where are firmware binaries stored or managed?
   - How `esptool` / serial flashing is executed from Pi5?
   - How all drone control / flight features are strictly locked until firmware is successfully flashed?
4. Investigate the ARM locking fail-safe mechanism:
   - Where in the backend is ARM controlled?
   - How geofence / MOD flight permission interacts with ARM validation?
   - Strict fail-safe: missing data, expired window, or >1km -> ARM locked! (NEVER set ENABLE_REAL_FLIGHT_COMMANDS=true).
5. Review the security requirements in Section 13:
   - Default password `123456` for `pi5` and SSH key transition, disabling password auth and root login.
   - Fail2ban integration, firewall ports (443, 22, 5353).
   - Rate limiting, CSRF/XSS/SQLi protections, cookie security (HttpOnly, Secure, SameSite).
   - Serial authentication and GPS spoofing detection.
   - Audit logging table (`audit_log`) and sensitive action coverage.

Deliverables:
- `/home/pnt/IOT/.agents/explorer_v2_survey_2/report.md`
- `/home/pnt/IOT/.agents/explorer_v2_survey_2/handoff.md`
- Message to parent via `send_message`.
