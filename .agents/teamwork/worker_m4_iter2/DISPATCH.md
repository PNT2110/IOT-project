# DISPATCH: Milestone 4 Worker (Iteration 2 Remediation)

**Assigned Agent**: `worker_m4_iter2`
**Working Directory**: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m4_iter2`
**Parent Conversation ID**: `3be5ec9a-8b7d-4356-b0b8-0a206dabba81`

---

## 1. Objective
Remediate all defects identified by Reviewers 1 & 2 and Challengers 1 & 2 during Milestone 4 Iteration 1:

### 1.1 Contract Path Requirements (Tier 1 E2E Test Fixes)
1. **`frontend/src/components/ErrorBanner.tsx`**:
   - Ensure `frontend/src/components/ErrorBanner.tsx` exists and exports `ErrorBanner`.
   - You can move `ErrorBanner.tsx` here or re-export from `common/ErrorBanner.tsx`.
   - Required by `tests/e2e/test_tier1_feature_coverage.py:388`.
2. **`frontend/src/components/operations/TelemetryPanel.tsx`**:
   - Extract the telemetry display from `OperationsWorkspace.tsx` into `frontend/src/components/operations/TelemetryPanel.tsx`.
   - Export `TelemetryPanel`.
   - Import and render `<TelemetryPanel ... />` in `OperationsWorkspace.tsx`.
   - Required by `tests/e2e/test_tier1_feature_coverage.py:405`.

### 1.2 Telemetry Polling Effect Loop (Eliminate Request Flood)
- In `TelemetryPanel.tsx` (and `OperationsWorkspace.tsx`), REMOVE `lastTelemetryReceived` from the `useEffect` dependency array!
- Use a `useRef<number | null>(null)` (`lastTelemetryReceivedRef`) for the elapsed age ticker.
- The telemetry fetch interval must run on mount (`[]`), polling strictly once every 1000ms.

### 1.3 ErrorBanner Timer Starvation (Parent Re-render Timer Reset)
- In `ErrorBanner.tsx`, store `onDismiss` in a ref (`const onDismissRef = useRef(onDismiss); onDismissRef.current = onDismiss;`).
- Only reset the timer when `message` or `autoDismissMs` changes: `useEffect(..., [message, autoDismissMs])`.
- This ensures parent re-renders (from the 500ms `ageTicker`) do NOT restart the 8-second timer.

### 1.4 Web Audio API Chime Cleanup & Autoplay Handling
- In `playNotificationChime()`, close the `AudioContext` after playback finishes (`window.setTimeout(() => void ctx.close().catch(() => {}), 500)`), or reuse a shared singleton `AudioContext`.
- Add `.catch(() => {})` on `ctx.resume()`: `void ctx.resume().catch(() => {})`.

### 1.5 Dark Mode Contrast & `.ghost-button` Fix
- In `frontend/src/experience.css` under `@media (prefers-color-scheme: dark)`:
  - Add `.ghost-button { background: var(--surface); color: var(--ink); border-color: var(--line-strong); }` and `.ghost-button:hover { background: var(--surface-soft); }`.
  - Adjust `--quiet: #8cb3d4;` in dark mode to ensure >4.5:1 contrast against `--surface` (`#142130`).

### 1.6 Smooth Leaflet Map Updates in `GpsMap`
- In `GpsMap` (or inside `TelemetryPanel.tsx`), preserve the `L.Map` instance using `useRef`. Initialize once on mount; on `[lat, lon]` change, update marker with `markerRef.current.setLatLng([lat, lon])` and `mapRef.current.panTo([lat, lon])` instead of calling `map.remove()`.

---

## 2. Exclusive Write Ownership
You exclusively own:
- `frontend/src/components/ErrorBanner.tsx`
- `frontend/src/components/common/ErrorBanner.tsx`
- `frontend/src/components/operations/TelemetryPanel.tsx`
- `frontend/src/components/operations/OperationsWorkspace.tsx`
- `frontend/src/experience.css`
- `frontend/src/api.ts`
- `frontend/src/types.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/account/AccountMenu.tsx`
- `frontend/src/components/auth/AuthPanel.tsx`

---

## 3. Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

---

## 4. Verification Requirements
You MUST run and verify:
1. `cmd /c npm --prefix frontend run typecheck` (must exit 0 with 0 errors).
2. `cmd /c npm --prefix frontend run build` (must exit 0 with 0 errors).
3. `pytest tests/e2e/test_tier1_feature_coverage.py -k "feature_12 or feature_13 or feature_14 or feature_15 or feature_16 or feature_17" -v` (ALL 6 tests must PASS).
4. `pytest tests/scope01 tests/scope02 tests/scope03 tests/scope04 tests/scope05 -q` (regression must pass).

---

## 5. Deliverables
Write your handoff report to:
`c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m4_iter2\handoff.md`
Update `progress.md`.
Send a completion message back to parent orchestrator (`3be5ec9a-8b7d-4356-b0b8-0a206dabba81`).

## 2026-10-03T23:47:40Z
[Message] timestamp=2026-10-03T23:47:40Z sender=3be5ec9a-8b7d-4356-b0b8-0a206dabba81 priority=MESSAGE_PRIORITY_HIGH content=You are worker_m4_iter2, Milestone 4 Worker (Iteration 2 Remediation).
Your working directory is: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m4_iter2
The authoritative requirements are in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md
The project specification is in: c:\Users\pnt21\Desktop\IOT\PROJECT.md
The detailed dispatch instructions are in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m4_iter2\DISPATCH.md
The review and challenger reports are in:
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\reviewer_m4_1\handoff.md
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\reviewer_m4_2\handoff.md
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m4_1\handoff.md
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m4_2\handoff.md
Implement all 6 remediations.

