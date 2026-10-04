# DISPATCH: Milestone 4 Worker (PC Frontend UI/UX & Features)

**Assigned Agent**: `worker_m4`
**Working Directory**: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m4`
**Parent Conversation ID**: `3be5ec9a-8b7d-4356-b0b8-0a206dabba81`

---

## 1. Objective
Implement all PC frontend requirements per `ORIGINAL_REQUEST.md` and `PROJECT.md`:
1. **Dark Mode Theme**:
   - Add `@media (prefers-color-scheme: dark)` token overrides in `frontend/src/experience.css` (or `styles.css`).
   - Replace/override all ~40 hardcoded `#fff` and light backgrounds on cards (`.editor-card`, `.table-card`, `.flight-card`, `.zone-card`, `.modal-content`, `.terms-dialog`, `.profile-dialog`, `.account-popover`, `.empty-state`, `.map-section`, `.topbar`, etc.) so they adapt cleanly to dark mode.
   - Adjust `.brand-mark` blend mode (`mix-blend-mode: normal` and appropriate filter in dark mode) so the logo remains clear and crisp.
   - Add CSS filter inversion to `.leaflet-tile-pane` in dark mode to invert standard raster tiles into dark control-room cartography.
2. **OperationsWorkspace Loading Indicators**:
   - Add `initialLoading` state in `frontend/src/components/operations/OperationsWorkspace.tsx`.
   - Show skeleton placeholders or an accessible loading spinner (`role="status"`, `aria-live="polite"`) during initial fetch.
   - Ensure `aria-busy` is accurately set on the workspace container during initial load and busy actions.
   - Prevent flash of empty state text prior to data resolution.
3. **8-Second Auto-Dismissing Error Banners**:
   - Implement an accessible error banner component or behavior with an 8-second auto-dismiss timer.
   - Provide a manual dismiss button (`×`, `aria-label="Đóng thông báo"`).
   - Preserve `role="alert"` and semantic HTML accessibility across all banner sites (`App.tsx`, `OperationsWorkspace.tsx`, `AccountMenu.tsx`, `AuthPanel.tsx`).
4. **Real-Time Telemetry Display**:
   - Add API function in `frontend/src/api.ts` to fetch `/api/v1/telemetry/latest`.
   - Add a telemetry view/tab or panel in `OperationsWorkspace.tsx` displaying:
     - Live GPS coordinates (latitude, longitude formatted to 6 decimal places).
     - Altitude in meters.
     - Battery percentage (with color thresholds: green/amber/red).
     - Live status chip (VALID_FIX / NO_FIX / STALE) and relative timestamp age (`< 2s`).
     - Polling interval of 1 second to guarantee update within the 2-second requirement.
5. **Flight Request Notifications**:
   - Implement background polling (every 3 seconds) for flight requests.
   - Detect newly submitted flights (`status === "SUBMITTED"`) not previously seen.
   - Display a visual badge count on the flights tab / header.
   - Show an on-screen toast/banner notification with flight details and a quick action button.
   - Play a subtle, non-intrusive Web Audio API chime (two-tone 880Hz -> 1320Hz synthesize, no external audio files required, fails gracefully if audio context is blocked by autoplay policy).
6. **GeoJSON & CSV Export Triggers**:
   - Add "Xuất GeoJSON" button in the Zones view to download zone data formatted as RFC 7946 GeoJSON `FeatureCollection`.
   - Add "Xuất CSV" button in the Flights view to download flight request history formatted as RFC 4180 CSV (with RFC 4180 escaping and quoting for special characters).

---

## 2. Exclusive Write Ownership
You exclusively own:
- `frontend/src/experience.css`
- `frontend/src/styles.css`
- `frontend/src/api.ts`
- `frontend/src/types.ts`
- `frontend/src/components/operations/OperationsWorkspace.tsx`
- `frontend/src/components/common/ErrorBanner.tsx` (or new helper components in `frontend/src/components/`)
- `frontend/src/App.tsx` (for global error banner / notification integration if needed)
- `frontend/src/components/auth/AccountMenu.tsx` (for ErrorBanner integration)
- `frontend/src/components/auth/AuthPanel.tsx` (for ErrorBanner integration)

---

## 3. Strict Verification & Integrity Requirements
- **MANDATORY INTEGRITY WARNING**:
  DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A `teamwork_preview_auditor` will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
- You MUST run `cmd /c npm --prefix frontend run typecheck` (`tsc --noEmit`) and ensure 0 TypeScript errors.
- You MUST run `cmd /c npm --prefix frontend run build` (`tsc -b && vite build`) and ensure 0 build errors.
- Do NOT break existing Vietnamese button names or text tested in `tests/scope01/browser_e2e.py` (e.g. `Đăng nhập / Đăng ký`, `Tài khoản đang chờ duyệt`, `Đăng xuất`).

---

## 4. Deliverables
Write your comprehensive completion report to:
`c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m4\handoff.md`
Update `progress.md` in your directory.
Send a completion message back to parent orchestrator (`3be5ec9a-8b7d-4356-b0b8-0a206dabba81`).
