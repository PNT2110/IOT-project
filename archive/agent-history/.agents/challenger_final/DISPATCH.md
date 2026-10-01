## 2026-09-13T13:34:30Z

You are the Final Challenger for the IOT Drone Station v2 project upgrade.
Your working directory: /home/pnt/IOT/.agents/challenger_final
User request record: /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (read section ## 2026-09-13T09:30:16Z)
Specification file: /home/pnt/IOT/prompt-du-an-drone-v2.md
Project documentation: /home/pnt/IOT/PROJECT.md, /home/pnt/IOT/TEST_READY.md, /home/pnt/IOT/TEST_REPORT.md
Test runner: /home/pnt/IOT/tests/ssh_test_runner.py

Your Mission:
Adversarially and empirically verify the correctness, robustness, and safety limits of the v2 upgrade:
1. Execute Test Scenarios:
   - Run the 16 automated SSH test scenarios in remote mode:
     `python3 /home/pnt/IOT/tests/ssh_test_runner.py --mode=remote --host 192.168.1.118 --user pi5`
   - Run the 16 automated SSH test scenarios in bench mode:
     `python3 /home/pnt/IOT/tests/ssh_test_runner.py --mode=bench`
   - Verify that all 16 scenarios pass cleanly.
2. Adversarial Safety & Fail-Safe Stress Testing:
   - Challenge 1: Fail-safe ARM Lockout without Permit. Send `POST /api/v1/commands/arm` without valid permit. Confirm 403 Forbidden rejection and lock down.
   - Challenge 2: Boundary Distance Violation. Send ARM command with coordinates at 1001m (>1km) from permit center. Confirm rejection.
   - Challenge 3: Time Window Violation. Send ARM command when current time is outside the valid permit window. Confirm rejection.
   - Challenge 4: Pre-Flash Lockout. Set firmware_flashed to false in test. Confirm all flight commands return 423 Locked.
   - Challenge 5: Serial Watchdog Timeout. Verify ESP32 watchdog logic in `FC_can_bang.ino` disarms when heartbeat > 2000ms.
   - Challenge 6: Anti-Replay on MOD Server. Replay an identical flight request payload with the same nonce/timestamp. Confirm 403 Forbidden rejection.
3. Issue your verdict: `APPROVE` or `REQUEST_CHANGES`.

Deliverables:
- Write report to `/home/pnt/IOT/.agents/challenger_final/report.md`
- Write handoff to `/home/pnt/IOT/.agents/challenger_final/handoff.md` with clear verdict: APPROVE or REQUEST_CHANGES
- Send completion message to parent via send_message.
