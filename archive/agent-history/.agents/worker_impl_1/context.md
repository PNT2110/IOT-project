# Worker Implementation Context
Assigned to implement M1 + M2 + M3:
- USB Serial migration for GPS (38400 baud)
- Content-based UsbPortCoordinator auto-detection (GPS NMEA vs ESP32 JSONL)
- Hardware reset protection (dtr=False, rts=False)
- SerialWorker thread safety and responsive shutdown
- Config and lifespan updates
Directory: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\worker_impl_1
Exclusive write ownership: backend/app/serial_io.py, backend/app/config.py, backend/app/main.py, backend/.env.example, PROJECT_STATUS.md, WORKLOG.md
Do NOT edit files in backend/tests/ (owned by test_writer).
