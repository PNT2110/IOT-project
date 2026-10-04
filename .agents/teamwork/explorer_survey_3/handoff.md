# Handoff Report: PC Frontend Architecture & Implementation Survey

**Explorer**: `explorer_survey_3` (PC Frontend Explorer)  
**Date**: 2026-10-03  
**Working Directory**: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_3`  
**Parent Conversation ID**: `3be5ec9a-8b7d-4356-b0b8-0a206dabba81`  

---

## 1. Observation

### 1.1 Build & Typecheck Tooling
- **Command & Output**: Executing `cmd /c npm run typecheck` inside `frontend/` runs `tsc --noEmit` and exited cleanly with code `0`:
  ```text
  > iot-research-pc-foundation-ui@0.1.0 typecheck
  > tsc --noEmit
  ```
- **Command & Output**: Executing `cmd /c npm run build` inside `frontend/` runs `tsc -b && vite build` and exited cleanly with code `0`:
  ```text
  > iot-research-pc-foundation-ui@0.1.0 build
  > tsc -b && vite build

  vite v7.3.6 building client environment for production...
  ✓ 93 modules transformed.
  dist/index.html                   0.52 kB │ gzip:   0.34 kB
  dist/assets/index-BUsTEjtL.css   97.96 kB │ gzip:  27.38 kB
  dist/assets/index-AHqGOWm7.js   701.72 kB │ gzip: 204.80 kB
  ✓ built in 4.84s
  ```
- **Dependencies (`frontend/package.json`)**: React 19.2.0, React DOM 19.2.0, Leaflet 1.9.4, `@geoman-io/leaflet-geoman-free` 2.20.2, `qrcode` 1.5.4, Vite 7.3.6, TypeScript 5.9.3.
- **Entry Points & Imports**:
  - `frontend/src/main.tsx` (lines 3–5):
    ```tsx
    import "./styles.css";
    import "./experience.css";
    import { App } from "./App";
    ```
  - Both CSS stylesheets are loaded in order (`styles.css` then `experience.css`).

---

### 1.2 Design Tokens & Dark Mode CSS Audit
- **Token Definitions**:
  - `frontend/src/styles.css` (lines 3–32):
    ```css
    :root {
      font-family: "Aptos", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
      color: #183650;
      background: #f2f7fc;
      --ink: #183650;
      --ink-soft: #395b77;
      --muted: #64809a;
      --quiet: #8299ad;
      --blue: #1689d5;
      --blue-deep: #086eae;
      --blue-wash: #e8f4fc;
      --sky: #dceefa;
      --surface: #ffffff;
      --surface-soft: #f6fafe;
      --canvas: #f2f7fc;
      --line: #d5e4ef;
      --line-strong: #bad4e7;
      --green: #137a55;
      --green-wash: #eaf7f1;
      --amber: #99620b;
      --amber-wash: #fff7e8;
      --red: #bd3445;
      --red-wash: #fff0f1;
      --radius-card: 18px;
      --radius-control: 9px;
      --shadow-card: 0 14px 38px rgba(28, 75, 111, 0.08);
    }
    ```
  - `frontend/src/experience.css` (lines 4–19):
    Redefines tokens with similar semantic names (`--ink`, `--ink-soft`, `--muted`, `--blue`, `--blue-deep`, `--blue-wash`, `--canvas`, `--surface-soft`, `--line`, `--line-strong`, `--shadow-card`, `--shadow-float`).
- **Hardcoded Backgrounds Bypassing Variables**:
  Over 40 selectors across `styles.css` and `experience.css` bypass `var(--surface)` or `var(--canvas)` and hardcode light colors:
  - `styles.css` line 93: `.topbar { background: rgba(255, 255, 255, .94); }`
  - `experience.css` line 39: `.topbar.portal-topbar { background: rgba(255, 255, 255, .96); }`
  - `experience.css` line 79: `.map-content-section .map-section { background: #fff; }`
  - `experience.css` line 149: `.editor-card, .table-card { background: #fff; }`
  - `experience.css` line 174: `.modal-content { background: #fff; }`
  - `experience.css` line 185: `.terms-dialog { background: #fff; }`
  - `experience.css` line 246: `.flight-card { background: #fff; }`
  - `styles.css` line 188: `.zone-card { background: #fff; }`
  - `styles.css` line 634: `.account-trigger { background: #fff; }`
  - `styles.css` line 660: `.account-popover { background: #fff; }`
  - `styles.css` line 674: `.profile-dialog { background: #fff; }`
  - `experience.css` line 99: `.map-search-row input { background: #f8fbfd; }`
  - `experience.css` line 156: `input, select, textarea { background: #f8fbfd; color: var(--ink); }`
- **Brand Mark Blend Mode**:
  - `styles.css` line 97: `.brand-mark { mix-blend-mode: multiply; }`
  - Against a dark background, `mix-blend-mode: multiply` causes the logo to turn black/invisible.
- **Cartographic Surface (Leaflet Maps)**:
  - `MapPanel.tsx` (line 58): uses standard OpenStreetMap raster tiles `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`.
  - In dark mode, standard OSM tiles are glaring white/light green/light yellow and clash with a dark control room interface unless an inversion CSS filter is applied to `.leaflet-tile-pane`.

---

### 1.3 OperationsWorkspace Loading Indicators
- `frontend/src/components/operations/OperationsWorkspace.tsx`:
  - Lines 56–59 define state arrays:
    ```tsx
    const [zones, setZones] = useState<Zone[]>([]);
    const [sources, setSources] = useState<ZoneSource[]>([]);
    const [flights, setFlights] = useState<FlightRequest[]>([]);
    const [accounts, setAccounts] = useState<Account[]>([]);
    ```
  - Lines 70–71 define action busy state:
    ```tsx
    const [busyAction, setBusyAction] = useState<string | null>(null);
    const busyRef = useRef(false);
    ```
  - Lines 87–96 fetch data on mount:
    ```tsx
    const refresh = async () => {
      const [zoneItems, sourceItems, flightData] = await Promise.all([listInternalZones(), listZoneSources(), listFlights()]);
      setZones(zoneItems);
      setSources(sourceItems);
      setFlights(flightData.items ?? []);
      setAccounts(canReviewAccounts ? (await listAccounts()).items ?? [] : []);
    };

    useEffect(() => { void refresh().catch((cause) => setError(cause instanceof Error ? cause.message : "Không tải được dữ liệu")); }, [user.id]);
    ```
  - **Absence of Initial Loading State**:
    There is no `loading` or `initialLoading` state in `OperationsWorkspace.tsx`. During the initial asynchronous `refresh()` call:
    - `busyAction` is `null`.
    - `busyRef.current` is `false`.
    - `aria-busy={busy}` on `<section className="workspace-section">` (line 183) evaluates to `false`.
    - The tab render immediately renders empty state text ("Chưa có vùng nào...", "Không có yêu cầu nào đang chờ.", "Không có tài khoản nào đang chờ duyệt.") before flipping to populated lists once the HTTP requests resolve.
    - No skeleton cards, pulse placeholders, or spinners exist.

---

### 1.4 Error Banner Lifecycles & Accessibility
- **Current Rendering Locations**:
  - `App.tsx` (line 75): `{error && <div className="error-banner portal-error" role="alert">{error}</div>}`
  - `OperationsWorkspace.tsx` (line 190): `{error && <div className="error-banner" role="alert">{error}</div>}`
  - `AccountMenu.tsx` (line 166): `{error && <div className="error-banner" role="alert">{error}</div>}`
  - `AuthPanel.tsx` (line 211): `{error && <div className="error-banner">{error}</div>}`
- **Current Behavior**:
  - Banners have no dismiss button (`<button aria-label="Đóng">×</button>`).
  - Errors persist indefinitely until an asynchronous action manually overwrites `setError(null)` or component unmounts.
  - Requirement specifically dictates 8-second auto-dismiss with manual dismiss capability while preserving `role="alert"` and semantic HTML.

---

### 1.5 New Capabilities
1. **Real-Time Telemetry View**:
   - `ORIGINAL_REQUEST.md` requirement: "A real-time telemetry display on the PC frontend that shows live GPS position, altitude, and battery data streamed from the Pi gateway... updated in real time (within 2 seconds of data arriving at the Pi)."
   - Pi telemetry structure (`edge/pi5/pi5/web/models.py` lines 137–157, `tests/scope05/test_esp_usb.py` lines 20–32):
     `latitude`, `longitude`, `altitude_m`, `fix_state`, `power: {battery_pct, voltage_v}`.
   - `frontend/src/api.ts` does not yet contain a telemetry endpoint function or model type.
   - `OperationsWorkspace.tsx` only has 3 tabs: `"zones" | "flights" | "accounts"`.
2. **Flight Request Notifications**:
   - `ORIGINAL_REQUEST.md` requirement: "PC operators receive a visible notification (on-screen badge, sound, or browser notification) when a new flight request is submitted."
   - Current state: `flights` is only loaded once at mount and on manual "Làm mới" button click. No background polling or notification mechanism exists.
3. **GeoJSON & CSV Export Triggers**:
   - `ORIGINAL_REQUEST.md` requirement: "An export button lets operators download zone data as GeoJSON and flight history as CSV."
   - Currently, neither the zones tab nor the flights tab provides an export trigger.

---

## 2. Logic Chain

### 2.1 Dark Mode Architecture
1. *Observation*: CSS variables (`--ink`, `--surface`, `--canvas`, `--line`, etc.) already define semantic roles, but elements have hardcoded `#fff` backgrounds, `.brand-mark` has `mix-blend-mode: multiply`, and Leaflet maps render bright raster tiles.
2. *Deduction*: Adding `@media (prefers-color-scheme: dark)` only to `:root` will leave all `#fff` cards, dialogs, popovers, and tables bright white.
3. *Recommendation*:
   - Define a complete dark token set in `experience.css`:
     ```css
     @media (prefers-color-scheme: dark) {
       :root {
         --ink: #e2ecf5;
         --ink-soft: #a2bed6;
         --muted: #799ab5;
         --quiet: #55748f;
         --blue: #29a0eb;
         --blue-deep: #54bcf7;
         --blue-wash: #122538;
         --sky: #19354d;
         --surface: #142130;
         --surface-soft: #192a3c;
         --canvas: #0c1622;
         --line: #22374c;
         --line-strong: #2f4b67;
         --green: #2ecc71;
         --green-wash: #0e2b1d;
         --amber: #f39c12;
         --amber-wash: #2e230b;
         --red: #e74c3c;
         --red-wash: #2f1217;
         --shadow-card: 0 16px 42px rgba(0, 0, 0, 0.52);
         --shadow-float: 0 24px 68px rgba(0, 0, 0, 0.72);
       }
       .topbar.portal-topbar, .topbar {
         background: rgba(19, 31, 45, 0.95);
         border-bottom-color: var(--line);
       }
       .editor-card, .table-card, .flight-card, .zone-card, .modal-content,
       .terms-dialog, .profile-dialog, .account-popover, .empty-state,
       .map-section, .map-toolbar, .account-trigger {
         background: var(--surface);
         border-color: var(--line);
         color: var(--ink);
       }
       .workspace-tabs {
         background: rgba(12, 22, 34, 0.95);
         border-bottom-color: var(--line);
       }
       .workspace-tabs button:hover {
         background: var(--surface-soft);
         border-color: var(--line);
       }
       .map-actions button, .map-home-button {
         background: var(--surface);
         color: var(--ink);
         border-color: var(--line-strong);
       }
       .map-legend {
         background: rgba(19, 31, 45, 0.94);
         border-color: var(--line);
         color: var(--ink);
       }
       .map-canvas {
         background: #0c1622;
       }
       .map-canvas .leaflet-tile-pane {
         filter: brightness(0.65) invert(1) contrast(2.6) hue-rotate(190deg) saturate(0.35) brightness(0.85);
       }
       .brand-mark {
         mix-blend-mode: normal;
         filter: brightness(1.1) drop-shadow(0 0 1px rgba(255, 255, 255, 0.3));
       }
       .secret-warning code {
         background: #1e1808;
         color: #f1c40f;
       }
       input, textarea, select {
         background: var(--surface-soft);
         color: var(--ink);
         border-color: var(--line-strong);
       }
     }
     ```

### 2.2 Loading Indicators & Skeleton Design
1. *Observation*: `OperationsWorkspace` has no `initialLoading` state, displaying empty content immediately during initial data load.
2. *Deduction*: Implementing `const [initialLoading, setInitialLoading] = useState(true)` allows displaying skeleton components or a dedicated loading spinner during initial mount.
3. *Recommendation*:
   - Set `initialLoading` to `true` initially and `false` when `refresh()` finishes.
   - Set `aria-busy={initialLoading || busy}` on the workspace section.
   - In `OperationsWorkspace.tsx`, render tab-appropriate skeleton placeholders when `initialLoading` is true (e.g. `<div className="skeleton-grid">...</div>`) or an accessible loading block:
     ```tsx
     {initialLoading ? (
       <div className="workspace-loading-state" role="status" aria-live="polite">
         <span className="spinner" aria-hidden="true" />
         <span>Đang tải dữ liệu điều hành…</span>
       </div>
     ) : ( ... )}
     ```

### 2.3 Auto-Dismissing Error Banners
1. *Observation*: Error banners render as plain text in `div.error-banner` without a dismiss button and without a timer.
2. *Deduction*: A reusable `ErrorBanner` component or `useAutoDismiss` hook can manage an 8000ms timer that clears on timeout, resets on error changes, cancels on unmount, and offers an immediate dismiss button `×`.
3. *Recommendation*:
   ```tsx
   export function ErrorBanner({ message, onDismiss, autoDismissMs = 8000 }: { message: string | null; onDismiss: () => void; autoDismissMs?: number }) {
     useEffect(() => {
       if (!message) return;
       const timer = window.setTimeout(onDismiss, autoDismissMs);
       return () => window.clearTimeout(timer);
     }, [message, onDismiss, autoDismissMs]);

     if (!message) return null;
     return (
       <div className="error-banner" role="alert" aria-live="assertive">
         <span>{message}</span>
         <button type="button" className="error-banner-dismiss" aria-label="Đóng thông báo" onClick={onDismiss}>×</button>
       </div>
     );
   }
   ```
   Add `.error-banner-dismiss` CSS:
   ```css
   .error-banner { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
   .error-banner-dismiss { background: transparent; border: 0; color: inherit; font-size: 1.3rem; line-height: 1; cursor: pointer; padding: 2px 6px; }
   ```

### 2.4 Real-Time Telemetry View
1. *Observation*: Pi gateway produces `latitude`, `longitude`, `altitude_m`, `battery_pct`, `voltage_v`, and `fix_state`. The PC frontend requires display within 2 seconds of arrival.
2. *Deduction*:
   - Add a 4th tab `"telemetry"` in `OperationsWorkspace.tsx`: `type Tab = "zones" | "flights" | "accounts" | "telemetry"`.
   - Add a polling interval of 1000ms (1s) to poll `/api/v1/telemetry/latest` (or WebSocket stream), safely well within the 2-second threshold.
   - Display:
     - Live GPS coordinates (latitude, longitude to 6 decimal places, e.g. `10.776900° N, 106.700900° E`).
     - Fix status chip (`VALID_FIX` / `NO_FIX` / `STALE`).
     - Altitude readout in meters with tabular numbers (`12.3 m`).
     - Battery readout with percentage (`83%`) and color threshold (green >= 50%, amber 20–49%, red < 20%).
     - Live pulse indicator (green dot + "TRỰC TIẾP" + relative age e.g. `< 1s trước`).
     - Live Leaflet map marker updating the drone's position in real time.

### 2.5 Flight Request Notification Mechanism
1. *Observation*: Flight requests are submitted asynchronously from Pi gateways via the device channel. Operators currently only see them if they manually refresh the flights tab.
2. *Deduction*:
   - Run a 3-second background polling cycle for `listFlights()`.
   - Maintain a set of previously known flight IDs in a `useRef<Set<string>>`.
   - When a newly submitted flight (`status === "SUBMITTED"` and `!knownFlightIds.current.has(flight.id)`) is detected:
     1. **Visual Badge**: Display a pulsing badge `({pendingFlights.length})` on the tab button and header.
     2. **On-Screen Toast/Banner**: Render a notification banner alerting the operator with applicant name, vehicle, and a quick "Xem ngay" button.
     3. **Audio Notification**: Play a short, clean two-tone chime (880Hz -> 1320Hz) via the browser's native `AudioContext` without requiring external audio files.
     4. **Browser Notification**: Trigger `new Notification(...)` if permission is granted.

### 2.6 GeoJSON & CSV Export Triggers
1. *Observation*: Operators need to download zone data as GeoJSON and flight request history as CSV.
2. *Deduction*:
   - **Zone GeoJSON Export**:
     Convert `zones` array to RFC 7946 GeoJSON `FeatureCollection`:
     ```ts
     const geojson = {
       type: "FeatureCollection",
       features: zones.map((z) => ({
         type: "Feature",
         id: z.id,
         properties: { id: z.id, name: z.name, classification: z.classification, visibility: z.visibility, version: z.version, retrieved_at: z.retrieved_at, source_id: z.source_id },
         geometry: z.geometry,
       })),
     };
     ```
     Trigger download via `Blob` (`application/geo+json;charset=utf-8`) as `zones-export-${date}.geojson`.
   - **Flight CSV Export**:
     Convert `flights` array to RFC 4180 CSV:
     Headers: `Mã yêu cầu,Người xin cấp,Bằng lái,Phương tiện,Thời gian bắt đầu,Thời gian kết thúc,Thiết bị,Trạng thái,Vĩ độ,Kinh độ,Lý do`.
     Properly quote/escape all fields to handle commas, newlines, and quotes (`replace(/"/g, '""')`).
     Trigger download via `Blob` (`text/csv;charset=utf-8`) as `flight-requests-${date}.csv`.

---

## 3. Caveats
1. **Physical GPS/ESP32 Hardware**: Testing on developer workstations operates against synthetic/mock telemetry or simulator adapters. The contract formats (`scope05.telemetry.v1`, `scope04.telemetry.v1`) must be maintained strictly.
2. **Audio Autoplay Policies**: Modern browsers require user interaction before playing audio via `AudioContext`. If audio is blocked before user gesture, the audio chime should gracefully fail without throwing uncaught errors while visual notifications proceed uninterrupted.
3. **Map Tile Provider**: OpenStreetMap raster tiles do not natively provide dark mode tiles without API keys. The CSS filter inversion approach on `.leaflet-tile-pane` provides an offline-friendly, dependency-free dark map that requires zero third-party API keys or license tokens.
4. **Existing E2E Playwright Tests**: `tests/scope01/browser_e2e.py` specifically asserts exact Vietnamese button names (e.g. `Đăng nhập / Đăng ký`, `Tài khoản đang chờ duyệt`, `Đăng xuất`). New features and UI enhancements must NOT alter these existing button texts or semantic headings.

---

## 4. Conclusion
1. The PC frontend (`frontend/`) is clean, modern, and in full working order: TypeScript 5.9.3 passes with zero errors (`tsc --noEmit`), and Vite 7.3.6 builds without errors.
2. The CSS token structure is already in place; Dark mode can be fully realized by:
   - Adding `@media (prefers-color-scheme: dark)` token overrides in `experience.css`.
   - Replacing hardcoded `#fff` backgrounds on cards, dialogs, and popovers with `var(--surface)`.
   - Inverting Leaflet raster tiles with CSS filters.
   - Adjusting `.brand-mark` blend mode.
3. Loading UX in `OperationsWorkspace.tsx` can be cleanly improved by introducing an `initialLoading` state, an animated skeleton/spinner placeholder, and updating `aria-busy`.
4. Error banners can be modernized into an accessible, 8-second auto-dismissing banner with a manual dismiss button (`×`), maintaining `role="alert"` and `aria-live="assertive"`.
5. The 3 requested frontend capabilities (real-time telemetry view, flight request notifications, and GeoJSON/CSV exports) have complete, concrete architectural designs that integrate into `OperationsWorkspace.tsx` and `api.ts`.

---

## 5. Verification Method

### 5.1 Typecheck & Production Build Verification
Execute from the project repository root:
```powershell
cmd /c npm --prefix frontend run typecheck
cmd /c npm --prefix frontend run build
```
- **Passing Condition**: Both commands exit with status code `0`.
- **Invalidation Condition**: Any TypeScript compilation error (`tsc --noEmit`) or Rollup/Vite bundling failure.

### 5.2 Dark Mode Verification
1. Open the frontend in Chromium / Firefox / Edge.
2. In Chrome DevTools, open the Command Palette (`Ctrl+Shift+P`) and run `Emulate CSS prefers-color-scheme: dark`.
3. Verify:
   - Map Overview page: background is dark navy (`#0c1622`), text is crisp light blue-gray (`#e2ecf5`), Leaflet map tiles render in inverted dark theme.
   - Operations Workspace: tabs, zone editor, flight cards, and accounts table render with dark surfaces (`#142130`) and legible contrast.
   - Brand logo is clearly visible and not blended away.

### 5.3 Loading State Verification
1. Throttle network speed to "Slow 3G" in DevTools.
2. Log in and navigate to `#workspace`.
3. Verify:
   - Skeleton/spinner placeholder is visible while data loads.
   - `aria-busy="true"` is present on the workspace section.
   - No flash of empty state text occurs prior to data arrival.

### 5.4 Error Banner Verification
1. Trigger an error (e.g., attempt to save a zone with empty name or invalid input).
2. Verify:
   - Banner appears immediately with `role="alert"`.
   - Banner has a functional dismiss button `×` that immediately removes the banner.
   - If left untouched, the banner automatically dismisses after exactly 8 seconds.

### 5.5 New Features Verification
1. **Telemetry View**: Check that GPS coordinates, altitude in meters, and battery percentage display clearly with < 2s update interval.
2. **Flight Request Notification**: Submit a flight request from a client or test script; verify on-screen alert banner, badge count update, and audio chime.
3. **Exports**: Click "Xuất GeoJSON" in the zones view and "Xuất CSV" in the flights view; verify browser initiates download and files contain valid GeoJSON (RFC 7946) and CSV (RFC 4180).
