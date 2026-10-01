## 2026-09-13T09:38:32Z
You are the Backend & Auth Worker for Milestone 2 (M2: Backend Core, DB Migrations & Auth System).
Your working directory: /home/pnt/IOT/.agents/worker_m2_backend
User request record: /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (read section ## 2026-09-13T09:30:16Z)
Specification file: /home/pnt/IOT/prompt-du-an-drone-v2.md (pay special attention to Sections 3, 4, 10, 11, 13)
Project documentation: /home/pnt/IOT/PROJECT.md
Explorer survey: /home/pnt/IOT/.agents/explorer_v2_survey_2/report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Boundaries:
You have exclusive write ownership of `backend/app/` (including `main.py`, `models.py`, `database.py`, `auth.py`, `wifi_handler.py`). DO NOT modify `frontend/` or `FC_can_bang/`.

Your Mission:
1. Syntax & Core Fixes in `backend/app/main.py`:
   - IMMEDIATELY eliminate all syntax errors in `backend/app/main.py` (lines 68, 147, 179, 348-364, 427, or wherever broken raw string literals or invalid parameter signatures exist).
   - Ensure `python3 -m py_compile backend/app/main.py` succeeds with 0 errors.
2. Database Models & Migrations (`database.py`, `models.py`):
   - Extend user schema with:
     - `full_name`: str
     - `dob`: str
     - `email`: str (unique)
     - `requested_role`: 'user' | 'admin'
     - `role`: 'user' | 'admin'
     - `approval_status`: 'approved' (for user) | 'pending' | 'rejected'
     - `is_default_admin`: bool
     - `first_login_completed`: bool
     - `email_otp`: str | None
     - `email_otp_expiry`: float | None
     - `totp_secret`: str | None
     - `totp_enabled`: bool
   - Create `audit_log` table: `id`, `timestamp`, `username`, `action`, `ip_address`, `status`, `details`.
   - Create migration logic in `database.py` so existing databases automatically gain these columns if missing.
3. User Registration & Auth Flows (`auth.py` / `main.py`):
   - `POST /api/v1/auth/register`:
     - Inputs: `full_name`, `dob`, `email`, `password`, `requested_role` ('user' | 'admin').
     - Hash password with Argon2id.
     - Generate 6-digit numeric email OTP (stored with 10-minute expiry).
     - If role is 'user', status is 'pending_otp' -> after OTP+2FA becomes 'approved' (User role).
     - If role is 'admin', status is 'pending_approval' (requires default admin approval after OTP+2FA).
   - `POST /api/v1/auth/verify-otp`:
     - Verifies email OTP. Returns TOTP provisioning secret / QR URL for 2FA.
   - `POST /api/v1/auth/verify-2fa`:
     - Verifies PyOTP TOTP code. Activates account.
   - `POST /api/v1/auth/login`:
     - Authenticates username/email + password + TOTP.
     - Issues session/JWT token.
     - Enforces first-login check for default admin `pi5`: if `is_default_admin == True` and `first_login_completed == False`, return response with `must_setup_admin: true` and restrict all other access.
   - `POST /api/v1/auth/admin-force-setup`:
     - Allows default admin `pi5` to update email, sends OTP to that email, verifies OTP, and sets `first_login_completed = True`.
   - `GET /api/v1/admin/pending-users` & `POST /api/v1/admin/approve-user`:
     - Allows approved admin to view and approve/reject pending admin registrations.
   - Role-based permissions:
     - Users with role 'user' can ONLY access the Camera stream endpoint and session info. All other tabs/endpoints return 403 Forbidden.
     - Admins in 'pending' status have same restricted permissions as 'user' until approved.
4. Wi-Fi Provisioning Serial Handoff (`wifi_handler.py`):
   - On receiving `{"type": "wifi_setup", "ssid": "...", "password": "..."}` over serial:
     - Executes network connection (via `nmcli` or mock in test mode).
     - Responds via serial with `{"type": "wifi_status", "status": "connected", "ip": "...", "url": "...", "drone_id": "...", "default_account": "..."}`.
5. Verification:
   - Run existing and updated backend tests: `PYTHONPATH=. pytest tests/`.
   - Ensure all tests pass.

Deliverables:
- Updated code in `backend/app/`
- Passing pytest results
- Work report in `/home/pnt/IOT/.agents/worker_m2_backend/report.md` and handoff in `/home/pnt/IOT/.agents/worker_m2_backend/handoff.md`
When done, notify parent via send_message.

## 2026-09-13T09:38:50Z
**Context**: Backend & Auth Worker for Milestone 2 (M2).
**Content**: You were assigned the M2 tasks (repair syntax errors in backend/app/main.py, database migrations for users/roles/audit_log, auth endpoints, first-login enforcement, and pytest verification).
**Action**: Please proceed with your assignment, report your current status, and deliver your handoff report when complete.
