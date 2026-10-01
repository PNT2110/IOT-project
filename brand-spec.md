# Drone Zone Check — brand spec

## Identity assets

- Primary logo: `frontend/public/logo-drone-zone-check.png` (user-supplied PNT / PVD Drone Zone Check artwork). Use the supplied file as-is; do not redraw or alter the lettering, colors, or mark.
- Product interface reference: screenshots supplied in the Codex conversation on 2026-09-30 and 2026-10-01. The intended public surface is the PC-server map portal; the same recognizable light-blue/white family applies across PC and Pi interfaces.
- Product model: F450 PNT PVD.

## Visual tokens

- Ink: `#183650`; secondary text: `#395B77` / `#64809A`.
- Primary action: `#1689D5`; deep action: `#086EAE`; pale blue surface: `#E8F4FC`.
- Canvas: `#F2F7FC`; primary surface: `#FFFFFF`; divider: `#D5E4EF`.
- Safety semantics: no-fly red `#BD3445`, restricted amber `#99620B`, available/approved green `#137A55`.
- Display/body type: Aptos / Segoe UI Variable stack for legibility and offline reliability; code/data: Cascadia Code / Consolas.
- Spacing basis: 4px; primary increments 8 / 12 / 16 / 24 / 32 / 48.
- Radius: 9px controls, 18px large panels; elevation reserved for map/workspace surfaces.
- Motion: short state feedback only; honor `prefers-reduced-motion`.

## Current redesign direction — 2026-10-01

- Mode: Redesign · Overhaul of presentation; preserve API routes, role gates, auth/MFA steps, form names/order, map capabilities and safety restrictions.
- Design read: public PC map portal and authenticated Pi operations dashboard; users are drone operators and reviewers; restrained cartographic operations UI rather than government branding.
- Calibration: visual variance 4/10, motion 2/10, information density 6/10 in operations and 3/10 on public portal, asset dependence 8/10, brand fidelity 10/10.
- Narrative / distance / temperature / capacity: map is the primary public content; readable from laptop and touch-sized on phone; calm and safety-forward; no decorative KPIs or fake official data.
- Preserve: supplied logo as-is, Vietnamese copy, exact project credit, public read-only map, Pi USB camera/ESP32 flows, role-aware modules, terms/authentication journeys, safe blocked ARM and firmware behavior.
- Improve: map-first hierarchy, scan-friendly operations panels, explicit empty/error states, mobile navigation and legibility.
- Remove: exposed JSON as default end-user presentation, ornamental service metrics, unsupported authority claims.
- Highest risk: making an internal/simulated decision look like a legal flight authorization; keep explicit local/internal and non-government wording.
- Fallback: keep raw diagnostics collapsed under “Dữ liệu kỹ thuật”; retain existing routes, IDs, and API contracts.

## Invariants

- Keep the exact supplied logo and the project credit “DỰ ÁN ĐƯỢC THỰC HIỆN BỞI PHẠM NGỌC TẤN VÀ PHAN VĂN ĐÔNG”.
- Keep Vietnamese copy, the public map read-only, the existing authentication/MFA journeys, role gates, route IDs, API contracts, and safe ARM/firmware restrictions.
- Do not invent official airspace data, permit approvals, telemetry, users, uptime, or other operational metrics.
