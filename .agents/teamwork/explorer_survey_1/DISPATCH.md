# Dispatch Task: Firmware & Pi Gateway Tier Survey

## Identity
- Role: Firmware & Gateway Explorer
- Working Directory: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1
- Parent Conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81

## Authoritative Requirements
c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md

## Scope & Objective
Perform an exhaustive survey of the Firmware tier (`firmware/`) and Pi Gateway tier (`edge/pi5/`) related to the project requirements:
1. Bug 1: Altitude throttle limiter in `firmware/FC_can_bang/flight_gate.h` (lines 59-83). Investigate `ALT_LIMIT_FLOOR_US`, `altitude_throttle_cap()`, `Baro.ino`, existing tests in `tests/firmware/test_flight_gate.cpp`, how tests are run (cmake, ctest, g++), what dynamic floor calculation makes physical sense for F450 drone.
2. Pi 5 Gateway & Local UI:
   - Investigate `edge/pi5/pi5/web/ui/app.js` (589 lines monolith using `h()` builder), styles, and assets.
   - Investigate how it connects to the Pi FastAPI backend (`edge/pi5/pi5/web/` or similar).
   - Investigate camera stream endpoints and how pause/resume control can be integrated.
   - Investigate OTA firmware update requirements for ESP32: does Pi backend have an OTA endpoint or does one need to be added? What is the upload flow for `.bin` files?
   - Investigate existing Pi test suites (`tests/scope05`, etc.) and how Pi services are tested.

## Scope Boundaries
- READ-ONLY investigation. Do NOT modify source code or tests.
- Verify facts by inspecting actual code files and test commands.

## Output Requirements
- Write your comprehensive survey report in `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1\handoff.md`.
- Include exact file paths, line numbers, function signatures, test command patterns, and concrete architectural recommendations.
- Update your `progress.md` and send a completion message back to the orchestrator.

## 2026-10-03T20:39:42Z
You are explorer_survey_1, the Firmware & Gateway Explorer.
Your working directory is: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1
The authoritative user requirements are in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md
Please read c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1\DISPATCH.md and c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md.

Execute the investigation of the Firmware tier (firmware/FC_can_bang/flight_gate.h, Baro.ino, tests/firmware/test_flight_gate.cpp, build/test mechanism) and Pi 5 Gateway & Local UI tier (edge/pi5/pi5/web/ui/app.js, camera stream pause/resume, OTA firmware update endpoints/flow, and tests in tests/scope05).
Write your detailed findings and architectural recommendations to c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1\handoff.md.
Update your progress.md and report back to parent (conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81) via send_message when done.

