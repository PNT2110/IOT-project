## 2026-09-13T09:32:12Z
You are Explorer 1 (Firmware & Serial Interface Specialist).
Your working directory is: /home/pnt/IOT/.agents/explorer_v2_survey_1
User request record: /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (read section ## 2026-09-13T09:30:16Z)
Specification file: /home/pnt/IOT/prompt-du-an-drone-v2.md (pay special attention to Sections 1, 2, 4, 10, 11)

Your Mission:
Conduct a comprehensive, read-only survey of the ESP32 flight controller code in `/home/pnt/IOT/FC_can_bang` and its serial/USB interaction with Pi5.
1. Inspect the entire directory structure and all files in `/home/pnt/IOT/FC_can_bang`. Document every file, header, and logic module.
2. Note the strict requirement: DO NOT CHANGE the directory/file structure of `FC_can_bang`. We only rewrite the internal logic.
3. Investigate the current build system (PlatformIO, Arduino CLI, ESP-IDF, Makefile, etc.) for `FC_can_bang`. How is it compiled and flashed?
4. Analyze how Wi-Fi AP mode and Captive Portal (DNS server, HTTP web server) should be implemented on ESP32 (WROOM) when unconfigured, including QR code / SSID generation and blue-white styling.
5. Analyze the serial protocol (115200 baud JSONL) between ESP32 and Pi5:
   - What messages/commands currently exist?
   - How to transmit Wi-Fi credentials from ESP32 to Pi5?
   - How to signal Pi5 connection status, IP/URL, drone ID back to ESP32 / captive portal?
   - How the ARM lock is commanded from Pi5 and enforced on ESP32?
   - How PID tuning parameters are exchanged?
6. Identify all technical constraints, dependencies, hardware abstractions, and failure modes.

Deliverables:
Write your full investigation report to `/home/pnt/IOT/.agents/explorer_v2_survey_1/report.md`.
Include:
- Complete file inventory of `FC_can_bang`
- Build & flash toolchain details
- Proposed Wi-Fi provisioning architecture (AP + captive portal + serial handoff)
- Serial JSONL protocol specifications (all messages, request/response formats)
- ARM locking fail-safe mechanism on ESP32
- Dependencies and risks

When done, write `/home/pnt/IOT/.agents/explorer_v2_survey_1/handoff.md` and send a message to parent via send_message with a brief summary and path to your report.
