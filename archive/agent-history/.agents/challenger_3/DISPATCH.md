## 2026-09-09T13:46:45Z

You are Challenger 3 (Adversarial Verifier).
Your working directory: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\challenger_3
Your parent conversation ID: 94568146-c35e-44d3-9a12-47c93b67809f

MANDATORY FIRST STEP:
Read c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\ORIGINAL_REQUEST.md.
Also read:
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\orchestrator_1\PROJECT.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\worker_remediate_1\handoff.md
- c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\challenger_1\handoff.md

TASK:
Empirically and adversarially verify the remediated UsbPortCoordinator and serial_io.py:
1. Verify that coordinate injection via forged *4A / *7B suffixes is completely blocked and returns None.
2. Verify that non-NMEA proprietary sentences are rejected by UsbPortCoordinator._probe_gps.
3. Run the adversarial challenger suite:
   cd backend && python -m pytest tests/test_adversarial_challenger.py -v
4. Render an adversarial verdict: APPROVE or REQUEST_CHANGES.
Write your report to:
c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\challenger_3\handoff.md
and send a completion message with your verdict to parent.
