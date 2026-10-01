# SCOPE-02 — Final report

**SCOPE-02 STATUS: `PASS_REPORTED`**
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)
**Phạm vi:** PC local-only simulated workflow/API. Dừng tại SCOPE-02; chưa mở SCOPE-03/04.

## P0 baseline

- Repo/root: `/home/pnt/IOT`; branch `main`; baseline HEAD `16dc418076b1a53a9d2fc9af482e3a514f0791f7`.
- Worktree: dirty với thay đổi/untracked SCOPE-00/SCOPE-01 hiện hữu; được bảo toàn, không reset/clean/stash/checkout/commit/push.
- Runtime: Python `3.14.7`, Node `v22.22.1`, npm `9.2.0`; không có DB runtime hay listener `8765/5173/8000` tại baseline.
- Blocker: không có blocker trong phạm vi SCOPE-02 sau khi chốt policy least-privilege; bootstrap Owner vẫn là local operational gate được ghi rõ, không HTTP self-activation.
- Chi tiết: [SCOPE02_BASELINE_REPORT.md](SCOPE02_BASELINE_REPORT.md).

## Đã thực hiện

| Task ID | File/area | Kết quả |
|---|---|---|
| S02-P1 | `server/app/models.py`, `schemas.py`, migration `9c4f2d7e6a11` | Account version, role elevation, simulated flight, idempotency, history; FK/check/index; Alembic forward/downgrade. |
| S02-P2-A | `server/app/api.py`, `services.py` | Account review list/detail; Owner-only status mutation; valid transitions; `If-Match`; revoke session; audit/history atomic. |
| S02-P2-R | `server/app/api.py`, `services.py` | Role elevation own/review/decision; duplicate/replay/key-reuse/stale guards; no Owner grant/self-review. |
| S02-P2-W | `server/app/api.py`, `services.py` | `DRAFT → SUBMITTED → UNDER_REVIEW → NEEDS_INFORMATION/REJECTED/APPROVED_SIMULATED`, resubmit, ownership, labels/source. |
| S02-P2-Pi | `server/app/api.py` | Read-only fake Pi v1 map/status; active-session + test identity; object scope; offline/stale. |
| S02-P2-B | `server/cli.py` | Explicit first Owner local activation requiring confirmation/password/TOTP, no HTTP bypass. |
| S02-P3 | `frontend/src/api.ts`, `App.tsx`, `styles.css` | Role-sensitive tabs/forms/status/errors; persistent `SIMULATED — NOT A FLIGHT PERMIT`; no new tiles/search. |
| S02-P4 | `tests/scope02/`, SCOPE-01 regression update | 6 SCOPE-02 tests + 13 SCOPE-01 tests; combined 19 pass. |
| S02-DOC | `contracts/v1`, `docs/09`, `docs/10`, `server/README`, reports | Contract, policy, rollback, deviations and evidence documented. |

## Kiểm thử

- `.venv/bin/pytest -q tests/scope01 tests/scope02 -W default` → exit `0`; **19 passed, 0 failed, 0 skipped**, 1 upstream AnyIO deprecation warning.
- `.venv/bin/python -m compileall -q server tests/scope01 tests/scope02` → exit `0`.
- `npm --prefix frontend run typecheck` → exit `0`.
- `npm --prefix frontend run build` → exit `0`, Vite `7.3.6`.
- `.venv/bin/pip check` → exit `0`, no broken requirements.
- `.venv/bin/pip-audit -r server/requirements.lock --format columns` → exit `0`, no known vulnerabilities.
- `npm --prefix frontend audit --omit=dev --audit-level=high` → exit `0`, 0 vulnerabilities.
- Alembic temp DB upgrade/repeat/downgrade/restore → exit `0`; `RESTORE_CHECK revision=9c4f2d7e6a11 tables=14`.
- Trusted Chrome HTTPS harness → exit `0`; screenshot [scope01-authenticated-dashboard.png](/tmp/scope01-browser-e2e-ynx60nu0/scope01-authenticated-dashboard.png), isolated CA/NSS only.
- `git diff --check` and application boundary/secret scans → exit `0`; no new prohibited route/field in application code, no private key/literal secret.

## Gate result

| Gate | Result | Evidence / reason |
|---|---|---|
| G0 Inventory | PASS | Baseline report, preserved dirty worktree, no Pi/firmware/public access. |
| G1 Contract/schema/migration/restore | PASS | v1 contract additions; revision `9c4f2d7e6a11`; temp upgrade/repeat/downgrade/restore. |
| G2 Account/RBAC/session/audit | PASS | Owner-only mutation, Admin read-only review, no self-review, revoke-on-suspend/reject, audit/history. |
| G3 Simulated workflow/concurrency/idempotency/labels | PASS | State matrix, `If-Match`, duplicate/key mismatch, stale reviewer, mandatory simulated label/source, boundary scan. |
| G4 Pi mock read-only/versioned/auth/object-scope/offline | PASS | GET-only `/api/v1/pi/v1/map|status`, fake identity, caller scope, `UNSYNCED`/`stale`; no external connection. |
| G5 regression/security/UI/browser/loopback | PASS | 19 tests, build/typecheck/audit, trusted browser, static secret/boundary scan, local-only harness. |
| G6 handoff/rollback/docs/owner acceptance | PASS_REPORTED | Reports, contract, rollback and owner decision list complete. Owner acceptance is still required before any later scope; no later scope was started. |

## Giới hạn và không được chạy

Không chạy Pi/SSH/webcam/GNSS/ESP32/firmware/hardware, external email/OTP, official map/authority API, public bind/tunnel, production TLS, PostGIS/load/concurrency benchmark hoặc deployment. Fake mail, fake Pi identity và workflow status chỉ là local test adapters; không phải giấy phép, phép đo hay chứng nhận an toàn/pháp lý. TOTP limiter vẫn process-local từ SCOPE-01.

## Quyết định cần owner

1. **Policy review:** A — giữ `OWNER_ONLY_REVIEW` (khuyến nghị); B — định nghĩa tập quyền cụ thể cho `ADMIN` ở scope sau.
2. **Bootstrap Owner:** A — chấp nhận CLI local-only + password/TOTP/confirmation (khuyến nghị); B — cung cấp quy trình vận hành khác trước scope sau.
3. **Retention:** A — chốt retention/legal hold ở scope tích hợp/deployment; B — cung cấp chính sách ngay bây giờ.

## Bước tiếp theo nhỏ nhất

Owner nghiệm thu báo cáo SCOPE-02 và chọn các quyết định trên. Sau đó mới lập scope tiếp theo; Codex không tự khởi động SCOPE-03/04.
