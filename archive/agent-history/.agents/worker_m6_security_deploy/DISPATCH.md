## 2026-09-13T13:16:45Z

You are the Security Hardening, Deployment & 16-Scenario Verification Worker (Milestone 6).
Your working directory: /home/pnt/IOT/.agents/worker_m6_security_deploy
User request record: /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (read section ## 2026-09-13T09:30:16Z)
Specification file: /home/pnt/IOT/prompt-du-an-drone-v2.md (pay special attention to Sections 11, 12, 13, and Table 12.1)
Project documentation: /home/pnt/IOT/PROJECT.md and /home/pnt/IOT/TEST_READY.md
Test runner: /home/pnt/IOT/tests/ssh_test_runner.py and /home/pnt/IOT/tests/common.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Pi5 Access Credentials:
- Host: 192.168.1.118
- User: pi5
- Current Password: 123456
- Python venv on Pi5: /opt/iot-drone/venv and /opt/drone-web-ui/venv
- Service on Pi5: drone-web-ui.service and/or iot-drone.service

Your Mission:
1. Deploy and Synchronize Code to Pi5:
   - Synchronize the updated repository files (`backend/`, `FC_can_bang/build/`, and `tests/`) to Pi5 at `/home/pi5/iot-drone` or the production directory.
   - Ensure the database migrations are applied to `/var/lib/iot-drone/drone.sqlite3` on Pi5.
   - Synchronize the compiled frontend `frontend/dist/` to Pi5 web serving root.
   - Start the independent MOD server on port 9000 (run as background systemd service or persistent background process).
   - Restart `drone-web-ui.service` / `iot-drone.service` on Pi5 and verify it is running cleanly (`journalctl -u drone-web-ui -n 50 --no-pager`).
2. Security Hardening (Section 13):
   - 13.1 Immediate Actions:
     * Generate secure SSH key pair on host, install public key into `pi5@192.168.1.118:~/.ssh/authorized_keys`, set proper permissions (`chmod 700 ~/.ssh`, `chmod 600 authorized_keys`), and verify SSH key-based authentication works cleanly without prompting for password.
     * Change the default password of user `pi5` (`123456`) to a strong password (e.g. `P15_Secur3_Dr0ne_2026!`), update ssh config/credentials accordingly.
     * Configure SSH daemon security if possible or document settings (`PasswordAuthentication no`, `PermitRootLogin no`).
   - 13.2 Security Audit & Checks:
     * 1. Firewall: inspect open listening ports (`ss -tlpn` / `nmap`) on Pi5; verify ports conform to declaration (443/tcp, 22/tcp, 5353/udp, 9000/tcp for MOD server).
     * 2. Web Authentication: verify rate-limiting on login/OTP, session expiry, secure cookies (`HttpOnly`, `SameSite`).
     * 3. CSRF / XSS / SQLi: verify input sanitization on flight requests, registration, and PID tuning.
     * 4. Serial Communication: verify ESP32 ⇄ Pi5 JSONL framing and command authentication.
     * 5. GPS Spoofing detection: verify speed jump and anomalous coordinate rejection in geofence engine.
     * 6. MOD Server: verify anti-replay timestamp/nonce and 1km geofence auto-expiry.
     * 7. Firmware Integrity: verify SHA-256 hash checks before flashing.
     * 8. Dependency Scan: run safety/audit checks on python packages.
     * 9. Audit Log: verify `audit_log` table records all sensitive actions.
   - Generate `/home/pnt/IOT/SECURITY_RISK_REPORT.md` detailing all identified vulnerabilities, risk levels (High/Medium/Low), remediation steps taken, and residual risk.
3. Execute All 16 Automated SSH Test Scenarios:
   - Run `python3 tests/ssh_test_runner.py --mode=remote --host 192.168.1.118 --user pi5` (using the SSH key or updated password).
   - Capture full execution logs for all 16 scenarios from Table 12.1.
   - Verify that all scenarios achieve passing status or genuine hardware/bench pass with clear diagnostic logging.
   - Update `/home/pnt/IOT/TEST_REPORT.md` with the live run results.
4. Document Assumptions:
   - Write `/home/pnt/IOT/ASSUMPTIONS.md` documenting every operational, architectural, and safety assumption made during implementation (e.g. ESP32 SoftAP grace period, MOD server WAN routing, LiDAR Kalman estimation fallback, etc.).
5. Check Definition of Done (Section 11):
   - Verify every single item in Section 11 is satisfied.

Deliverables:
- Deployment on Pi5
- SSH key configuration
- Full execution of 16 test scenarios logged to `/home/pnt/IOT/TEST_REPORT.md`
- `/home/pnt/IOT/SECURITY_RISK_REPORT.md`
- `/home/pnt/IOT/ASSUMPTIONS.md`
- Report in `/home/pnt/IOT/.agents/worker_m6_security_deploy/report.md` and handoff in `/home/pnt/IOT/.agents/worker_m6_security_deploy/handoff.md`
When done, notify parent via send_message.
