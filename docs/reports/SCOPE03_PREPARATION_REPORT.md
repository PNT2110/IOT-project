# SCOPE-03 — Preparation report

**STATUS:** `DESIGN_MOCK_ONLY / BLOCKED_FOR_LIVE_PI`
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)

## Đã chuẩn bị

- Đã đọc và đối chiếu `docs/12_NETWORK_ARCHITECTURE.md`, `docs/scopes/SCOPE03_PI_NETWORK.md`, `docs/scopes/SCOPE04_PI_WEB.md`, ADR-006/008 và policy amendment SCOPE-02.
- Đã tạo prompt triển khai kế tiếp: [CODEX_SCOPE03_PI_NETWORK_IMPLEMENTATION.md](../prompts/CODEX_SCOPE03_PI_NETWORK_IMPLEMENTATION.md).
- Kiến trúc giữ AP onboard và USB STA tách biệt; ba tín hiệu reachability độc lập; manual recovery URL; mock-first, typed adapter, no arbitrary shell/sudo.
- Chưa tạo code/config Pi, chưa SSH, chưa đổi network/firewall/DHCP/DNS/route, chưa reboot và chưa kết nối phần cứng.

## Hardware/field facts

| Evidence | Status | Ghi chú |
|---|---|---|
| Pi model/RAM/OS/kernel/arch | `UNVERIFIED` | Chưa truy cập Pi. |
| Onboard Wi-Fi interface/name/bus | `UNVERIFIED` | Không suy đoán tên interface. |
| USB Wi-Fi chipset/driver/managed+AP concurrency | `BLOCKED` | Chưa có `lsusb`/`iw`/regulatory evidence. |
| Current IP/subnet/router/DHCP/DNS | `UNVERIFIED` | `192.168.4.1/24` chỉ là proposal. |
| Console/keyboard/HDMI/recovery path | `UNVERIFIED` | Không được đổi mạng từ xa khi thiếu đường khôi phục. |
| PC↔Pi device identity/retention policy | `BLOCKED` | SCOPE-02 fake header không phải identity thật; retention/legal hold chưa chốt. |

## Live-network authorization questions

1. Owner cấp thời điểm và phạm vi lab cụ thể nào cho SCOPE-03 live? Cần model Pi/OS, USB dongle chipset/driver, nguồn, địa chỉ hiện tại, SSID/subnet lab và người trực.
2. Console/recovery độc lập nào sẽ giữ quyền truy cập nếu STA/AP lỗi? Nếu chỉ có một SSH session qua interface thay đổi, gate N0/N4 vẫn blocked.
3. Có cho phép tạo AP/DHCP/DNS profile tạm trong subnet lab cô lập không? Cần last-known-good snapshot và rollback command được phê duyệt trước.
4. Nếu dự kiến PC↔Pi status sync, retention/legal hold và device identity/TLS nào đã được owner chốt? Nếu chưa, chỉ status mock/local, không PII exchange.

## Planned manifest after authorization

| Classification | Planned area | Current state |
|---|---|---|
| `CREATE` | Pi network adapter/state/config/tests only after SCOPE-03 code approval | Not created |
| `CREATE` | `docs/reports/SCOPE03_*` execution reports | Not created; this is preparation only |
| `READ_ONLY` | `docs/12_NETWORK_ARCHITECTURE.md`, SCOPE-03/04 docs, PC contracts | Read and preserved |
| `FORBIDDEN` | Pi live config before authorization, firmware/ESP32/GNSS, public exposure, control path | Not touched |

## Rollback/recovery plan to approve before live work

1. Record redacted interface/profile/route/firewall/DHCP/DNS baseline and preserve last-known-good files.
2. Have physical/console operator present; do one network change per step and verify AP/manual URL before next step.
3. On STA failure, restore only the previous STA profile and keep AP unchanged; do not run broad reset/cleanup.
4. On loss of access, stop immediately and use console runbook; do not keep retrying remote changes.
5. Verify clean teardown and capture redacted evidence. Do not report AP continuity or USB concurrency as PASS without real lab evidence.

## Current gates

| Gate | Status | Reason |
|---|---|---|
| N0 | `BLOCKED` | Amendment is implemented/tested but owner acceptance of the amendment is not yet recorded; Pi inventory/recovery facts absent. |
| N1 | `DESIGN_READY` | Mock-first typed/state-machine plan prepared; no Pi code started in this turn. |
| N2 | `NOT_RUN` | No live config or lab subnet authorization. |
| N3 | `DESIGN_READY / MOCK_ONLY` | Semantics specified; no real probes. |
| N4 | `BLOCKED/NOT_RUN` | No Pi access or real client observation. |
| N5 | `DESIGN_READY` | Prompt/report/rollback boundary prepared; owner acceptance pending. |

## Stop condition

This turn stops after the PC policy amendment and SCOPE-03 design/mock preparation. No live Pi operation, SCOPE-04, SCOPE-05 or SCOPE-06 action was started.

## Continuation addendum — PC mock implemented 2026-09-22

The next approved mock-first turn created `pi5/network/`, `tests/scope03/` and `contracts/v1/SCOPE03_PI_NETWORK_MOCK.md`. The package contains typed status models, redacted profile validation/store, mock adapters, recovery simulation and a bounded AP/STA state machine. Combined SCOPE-01/02/03 tests pass (`29 passed`). This does not change the live boundary: `PI_READ_ONLY_INVENTORY=BLOCKED`, `LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED`, and N4 remains `BLOCKED/NOT_RUN`.
