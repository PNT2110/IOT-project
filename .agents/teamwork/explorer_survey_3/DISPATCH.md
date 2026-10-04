# Dispatch Task: PC Frontend Tier Survey

## Identity
- Role: PC Frontend Explorer
- Working Directory: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_3
- Parent Conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81

## Authoritative Requirements
c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md

## Scope & Objective
Perform an exhaustive survey of the PC Frontend tier (`frontend/`) and its build/typecheck tooling:
1. Design Tokens and Dark Mode:
   - Investigate CSS variables in `frontend/src/styles.css` and `frontend/src/experience.css` (`--ink`, `--surface`, `--canvas`, etc.).
   - Investigate how dark mode media query (`@media (prefers-color-scheme: dark)`) can be integrated cleanly without breaking any views (map, zones, flights, accounts).
2. Loading Indicators & Skeletons:
   - Inspect `frontend/src/components/operations/OperationsWorkspace.tsx` and related components.
   - Investigate current `busyAction` usage, initial data fetching, and where visual loading indicators (spinners/skeletons) are missing.
3. Auto-Dismissing Error Banners:
   - Investigate how errors and banners are currently managed and displayed across the frontend.
   - How to introduce 8-second auto-dismiss with remaining manual dismiss capability while preserving accessibility (`aria-*` attributes, semantic HTML).
4. New Features in Frontend:
   - Real-time telemetry view (GPS coordinates, altitude, battery percentage within 2 seconds of Pi gateway).
   - Flight request notifications for PC operators (on-screen badge, sound, or notification).
   - Export zone data as GeoJSON and flight history as CSV (buttons, download handling).
5. Build & Typecheck Setup:
   - Inspect `frontend/package.json`, `frontend/tsconfig.json`, build scripts (`npm run build`, `npm run typecheck` or `npx tsc --noEmit`).
   - Identify existing component architecture, routing, API client, and state management.

## Scope Boundaries
- READ-ONLY investigation. Do NOT modify source code or tests.
- Verify facts by inspecting actual code files and configuration.

## Output Requirements
- Write your comprehensive survey report in `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_3\handoff.md`.
- Include exact component paths, CSS token mappings, API hooks, state stores, type definitions, and concrete implementation recommendations.
- Update your `progress.md` and send a completion message back to the orchestrator.


## 2026-10-03T20:39:42Z
[Message] timestamp=2026-10-03T20:39:42Z sender=3be5ec9a-8b7d-4356-b0b8-0a206dabba81 priority=MESSAGE_PRIORITY_HIGH content=You are explorer_survey_3, the PC Frontend Explorer.
Your working directory is: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_3
The authoritative user requirements are in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md
Please read c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_3\DISPATCH.md and c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md.

Execute the investigation of the PC Frontend tier (frontend/src/, styles.css/experience.css dark mode media query, OperationsWorkspace.tsx loading spinners/skeletons, 8s auto-dismiss error banners with manual dismiss and aria-* preserved, real-time telemetry view, flight request notifications, GeoJSON/CSV export triggers, and package.json/typecheck build status).
Write your detailed findings and architectural recommendations to c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_3\handoff.md.
Update your progress.md and report back to parent (conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81) via send_message when done.
