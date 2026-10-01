# PROMPT CHO CODEX — SCOPE-03 PI NETWORK IMPLEMENTATION

**Trạng thái:** `DESIGN_READY_PENDING_LIVE_AUTHORIZATION`
**Ngày chuẩn bị:** 2026-09-22
**Phạm vi:** chỉ Pi 5 network/AP/USB STA/recovery/status; không Pi web đầy đủ, camera, telemetry, ESP32/GNSS, firmware hay public deployment.

## Preconditions bắt buộc

1. Owner đã nghiệm thu [SCOPE02_POLICY_AMENDMENT_FINAL_REPORT.md](../reports/SCOPE02_POLICY_AMENDMENT_FINAL_REPORT.md) và quyết định retention/legal hold trước mọi PC↔Pi exchange có PII.
2. Owner cấp riêng live-network authorization với model Pi/OS, onboard adapter, USB Wi-Fi chipset/driver, nguồn điện, địa chỉ hiện tại, thời gian thử, người trực, phương án console/keyboard/HDMI hoặc recovery độc lập SSH, subnet/SSID không xung đột và rollback approval.
3. Codex phải rebaseline repo/branch/HEAD/worktree/ports/Pi facts trước khi đụng config. Không dùng IP/SSID/password từ lịch sử.

## Bất biến an toàn

- Không SSH/sudo/reboot/đổi IP/đổi route/firewall/DHCP/DNS/bind AP nếu chưa có live authorization và recovery path đã kiểm tra.
- Onboard Wi-Fi duy trì AP cho client; USB Wi-Fi là STA upstream. Client không phải đổi Wi-Fi sau khi STA lên.
- `192.168.4.1/24` chỉ là proposal; phải kiểm tra overlap trước khi chọn subnet.
- Ba tín hiệu độc lập: `external_wifi_connected`, `internet_reachable`, `central_server_reachable`; mỗi tín hiệu có timestamp, latency/timeout, error code, `stale`, `source`. Khi chưa có authenticated PC device identity, central status là `UNVERIFIED/UNAVAILABLE`, không giả PASS.
- AP/local recovery phải giữ được khi STA sai mật khẩu, DHCP/Internet/PC down hoặc profile mới lỗi. Không bật forwarding/NAT/SSH từ AP mặc định.
- Không lấy `X-Fake-Pi-Client` của SCOPE-02 làm xác thực thật; không đưa secret, PSK, OTP, token, cert/key hoặc topology nhạy cảm vào log/report.
- Không có command channel, flight-control path hay thay đổi firmware.

## P0 — Read-only inventory/recovery gate

Chỉ sau khi được phép, chạy lệnh đọc để thu thập redacted: OS/kernel/arch, NetworkManager, `nmcli device/status`, `ip -brief addr`, route, interface↔bus, `lsusb`, `iw` modes/AP+managed capability, regulatory domain, subnet/router/DHCP/DNS, memory/disk/power. Chụp last-known-good profile/config trước thay đổi. Nếu chỉ có SSH qua interface sắp sửa, dừng `BLOCKED`.

## P1 — Mock-first implementation

Tạo typed/injected interfaces `NetworkManagerAdapter`, `ConnectivityProbe`, `ProfileStore`, `RecoveryController` và state machine mock với `AP_UP`, `AP_DEGRADED`, `STA_DISCONNECTED`, `STA_CONNECTING`, `STA_CONNECTED`, `STA_FAILED`, `INTERNET_UNKNOWN/UP/DOWN`, `PC_UNKNOWN/UP/DOWN`. Validate SSID/profile encoding/length/auth/interface; dùng argument arrays hoặc DBus typed calls, không shell string từ input; không cho web gọi sudo tùy ý.

## P2 — Contract/status/provisioning design

Contract tối thiểu gồm interface identity (`onboard_ap`, `usb_sta`, `verified`), `ap_reachable`, ba reachability signals, `observed_at`, `stale`, `source`, `error_code`, `manual_config_url`. AP config và STA config tách biệt. Captive portal best-effort, luôn có manual URL. Credentials chỉ ở system store đã duyệt, không URL/localStorage/log.

## P3 — Failure tests and approved lab only

Mock wrong password, unplug/replug, DHCP timeout, DNS-only, Internet down/PC up, Internet up/PC down, subnet conflict, malformed SSID, concurrent profile update, disk/process/reboot recovery. Lab Pi chỉ sau authorization: một thay đổi mỗi lần, người trực + console, kiểm tra AP liên tục, route/NAT/firewall/DHCP/DNS và teardown. Thất bại thì restore last-known-good STA nhưng giữ AP.

## Acceptance gates

- `N0`: SCOPE-02 amendment owner-approved; Pi facts and recovery verified.
- `N1`: typed adapters/state/validation/least privilege; no injection or secret leak.
- `N2`: AP/STA separation, addressing, DHCP/DNS/firewall and manual recovery URL.
- `N3`: three independent signals with unknown/stale semantics.
- `N4`: AP remains reachable through STA/upstream failure, evidenced on real lab client.
- `N5`: reports/rollback complete; no out-of-scope hardware/control integration.

Thiếu Pi facts/console/live authorization thì `N4=BLOCKED/NOT_RUN`, SCOPE-03 chỉ `PARTIAL (design/mock)`. Không mở SCOPE-04/05/06 khi chưa có owner acceptance.

## Deliverables

```text
docs/reports/SCOPE03_BASELINE_REPORT.md
docs/reports/SCOPE03_DECISIONS_AND_DEVIATIONS.md
docs/reports/SCOPE03_IMPLEMENTATION_REPORT.md
docs/reports/SCOPE03_TEST_REPORT.md
docs/reports/SCOPE03_FINAL_REPORT.md
```

Phân biệt rõ `TESTED_ON_PC_MOCK`, `TESTED_ON_PI_LAB`, `NOT_RUN`, `BLOCKED`, `DEFERRED_BY_SCOPE`; không biến mock reachability thành số đo thật.
