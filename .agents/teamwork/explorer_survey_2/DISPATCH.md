# Dispatch Task: Server Backend Tier Survey

## Identity
- Role: Server Backend Explorer
- Working Directory: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_2
- Parent Conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81

## Authoritative Requirements
c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md

## Scope & Objective
Perform an exhaustive survey of the PC Server Backend tier (`server/`) and related test suites (`tests/scope01`–`07`):
1. Bug 2: Non-blocking email sending in `server/app/mail.py` (lines 61-71, `SmtpEmailSender.send_code()`). Examine how email sender is used in the app, how `asyncio.to_thread` or native async should be applied, and existing email mocks/tests.
2. Bug 3: Email normalization in `server/app/security.py` (lines 27-28, `normalize_email()`). Examine Gmail dot-stripping, subaddress (`+tag`) removal, domains affected, and how tests in `tests/scope01` (or auth tests) exercise normalization.
3. Telemetry Stream API:
   - How does the server currently receive telemetry from Pi or drones? (HTTP, WebSocket, MQTT, etc. in `server/app/routers/` or services).
   - What endpoint does the PC frontend use or need to query/subscribe to live telemetry (GPS, altitude, battery within 2s of Pi)?
4. Flight Request Notification API:
   - How are flight requests created (`server/app/routers/` or `services/flight_requests.py` / `operations.py`)?
   - How can PC operators receive notifications (polling, SSE, WebSocket, or notification endpoint)?
5. Export API:
   - Zone data export as GeoJSON format (RFC 7946 standard).
   - Flight history export as CSV format.
   - Where are existing zone and flight models/queries defined, and what endpoints should provide these exports?
6. Pytest Suites:
   - Survey test runner setup (`pytest`, `tests/scope01` to `tests/scope07`), test dependencies, and how tests are executed.

## Scope Boundaries
- READ-ONLY investigation. Do NOT modify source code or tests.
- Verify facts by inspecting actual code files and test commands.

## Output Requirements
- Write your comprehensive survey report in `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_2\handoff.md`.
- Include exact file paths, line numbers, schemas, data models, router endpoints, test commands, and concrete implementation recommendations.
- Update your `progress.md` and send a completion message back to the orchestrator.


## 2026-10-03T20:39:42Z
You are explorer_survey_2, the Server Backend Explorer.
Your working directory is: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_2
The authoritative user requirements are in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md
Please read c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_2\DISPATCH.md and c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md.

Execute the investigation of the PC Server Backend tier (server/app/mail.py non-blocking async, server/app/security.py email normalization, telemetry ingestion & real-time streaming to PC frontend within 2s, flight request operator notification mechanism, zone GeoJSON export & flight history CSV export, pytest setup in tests/scope01-tests/scope07).
Write your detailed findings and architectural recommendations to c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_2\handoff.md.
Update your progress.md and report back to parent (conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81) via send_message when done.
