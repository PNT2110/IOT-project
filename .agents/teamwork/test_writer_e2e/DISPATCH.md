# Dispatch Task: E2E Testing Track — Test Suite Creation

## Identity
- Role: E2E Test Suite Writer
- TypeName: teamwork_preview_test_writer
- Working Directory: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\test_writer_e2e
- Parent Conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81

## Authoritative Requirements & References
- Requirements: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md`
- Project Spec: `c:\Users\pnt21\Desktop\IOT\PROJECT.md`
- Explorer Reports: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1\handoff.md`, `explorer_survey_2\handoff.md`, `explorer_survey_3\handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All test cases must be genuine and thorough. DO NOT hardcode trivial pass tests or create facade assertions. An auditor will verify all test cases.

## Exclusive Write Ownership
You exclusively own and may edit ONLY the following files:
1. `TEST_INFRA.md` at project root `c:\Users\pnt21\Desktop\IOT\TEST_INFRA.md`
2. `tests/e2e/` (test harness, runners, test cases across Tiers 1-4)
3. `TEST_READY.md` at project root `c:\Users\pnt21\Desktop\IOT\TEST_READY.md`
DO NOT modify implementation code or existing test suites (`tests/scope01`-`scope07`, `tests/firmware/`).

## Detailed Tasks
1. **Design E2E Test Infrastructure (`TEST_INFRA.md`)**:
   - Establish opaque-box, requirement-driven test philosophy derived from `ORIGINAL_REQUEST.md` and `PROJECT.md § Feature Inventory`.
   - Implement test runner capable of executing all E2E tests independently via `pytest tests/e2e/`.
2. **Build Comprehensive 4-Tier Test Suite in `tests/e2e/`**:
   - **Tier 1 - Feature Coverage**: Cover all 18 features in `PROJECT.md § Feature Inventory` with clean equivalence class representatives (happy paths, isolation).
   - **Tier 2 - Boundary & Corner Cases**: Edge cases, empty inputs, limits, malformed inputs, email alias variations, extreme altitudes, maximum flight time bounds.
   - **Tier 3 - Cross-Feature Combinations**: Pairwise interactions (e.g. flight request creation + operator notification, sealed telemetry ingestion + PC live query, zone creation + GeoJSON export).
   - **Tier 4 - Real-World Application Scenarios**: Complete end-to-end mission workflows (pilot logs in, submits flight request in restricted zone, operator reviews request, drone streams telemetry, operator exports flight CSV and zone GeoJSON).
3. **Publish `TEST_READY.md`**:
   - Once the test harness and test cases are ready, publish `c:\Users\pnt21\Desktop\IOT\TEST_READY.md` with:
     - Test runner command
     - Coverage summary table by Tier
     - Feature checklist mapping
4. **Handoff**:
   - Write comprehensive report to `handoff.md`, update `progress.md`, and notify parent orchestrator via `send_message`.


## 2026-10-03T20:54:53Z
You are test_writer_e2e, the E2E Test Suite Writer.
Your working directory is: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\test_writer_e2e
The authoritative requirements are in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md
The project specification is in: c:\Users\pnt21\Desktop\IOT\PROJECT.md
The detailed dispatch instructions are in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\test_writer_e2e\DISPATCH.md
Survey handoffs:
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1\handoff.md
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_2\handoff.md
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All test cases must be genuine and thorough. DO NOT hardcode trivial pass tests or create facade assertions. An auditor will verify all test cases.

You exclusively own:
- c:\Users\pnt21\Desktop\IOT\TEST_INFRA.md
- tests/e2e/ (test harness and test suites across Tiers 1-4)
- c:\Users\pnt21\Desktop\IOT\TEST_READY.md

Design and write the comprehensive opaque-box E2E test suite covering all features in PROJECT.md § Feature Inventory.
Include Tier 1 (Feature coverage), Tier 2 (Boundary & Corner cases), Tier 3 (Cross-feature combinations), Tier 4 (Real-world application scenarios).
Run pytest tests/e2e/ to ensure the test harness is executable and tests are properly structured.
When test suite is complete, publish TEST_READY.md.
Write your completion report in c:\Users\pnt21\Desktop\IOT\.agents\teamwork\test_writer_e2e\handoff.md, update progress.md, and send a completion message to parent orchestrator (conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81).
