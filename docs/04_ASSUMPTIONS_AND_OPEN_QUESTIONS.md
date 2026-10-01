# SCOPE-00 — Assumptions, BLOCKED và câu hỏi mở

## Blocker ưu tiên P0

| ID | Câu hỏi/bằng chứng cần có | Vì sao chặn |
|---|---|---|
| Q-P0-01 | Model/variant ESP32 và board pinout chính xác? | GPIO, UART, boot strap và mức điện phụ thuộc board. |
| Q-P0-02 | Model GNSS, datasheet/ảnh tem, logic voltage, nguồn, dây RX/TX, giao thức/baud thực đo? | Không thể chọn parser, level shifting hay claim NMEA/UBX. |
| Q-P0-03 | SBUS đang dùng GPIO nào ngoài source `GPIO35` RX? GNSS có dùng chung UART không? | Tránh xung đột UART và mất điều khiển. |
| Q-P0-04 | Model/driver/PHY capability and Raspberry Pi OS version/kernel for the owner single-radio profile? | Same-PHY AP+STA, channel synchronization and recovery behavior are not independently verified. |
| Q-P0-05 | PC OS/path chuẩn, target deployment và quyền sửa repo? | SCOPE-01 phải biết runtime nhưng không được đoán. |
| Q-P0-06 | Nguồn dữ liệu vùng bay nào được cấp quyền dùng, license, API/format, cập nhật và contact? | Không được scrape/re-distribute dữ liệu pháp lý không rõ quyền. |

## P1 — cần trả lời trước integration

- Camera model, `/dev/video*`, resolution/fps mong muốn và có chấp nhận MJPEG prototype không?
- Pi và PC có đồng hồ/time source nào; timezone lưu UTC hay local display?
- Email provider/sender domain nào; có môi trường test sandbox không?
- Owner bootstrap do ai giám sát; recovery khi mất TOTP/email là quy trình nào?
- Retention cho hồ sơ, telemetry, video, audit và recovery codes?
- Pi ↔ PC có cần outbound-only mTLS/VPN hay chỉ LAN? Server có public URL không?
- Khi email OTP unavailable, UX mong muốn là “chặn login” hay cho phép read-only session đã xác thực trước? Không được tự bypass.

## Assumptions tạm thời (không phải facts)

1. PC local development có thể chạy Python/Node nhưng chưa đo phiên bản.
2. Owner target is onboard single-radio `wlan0` managed STA + `ap0` AP; capability, same-channel operation and boot persistence remain pending live validation.
3. Canonical time là UTC ISO 8601; client hiển thị Asia/Ho_Chi_Minh khi user chọn.
4. `SIMULATED` là default workflow state và không phát lệnh actuator.
5. Geometry canonical là GeoJSON WGS84 `[longitude, latitude]` theo RFC 7946.

## Bằng chứng cần thu thập ở scope sau

Không yêu cầu trong SCOPE-00: `uname -a`, `nmcli device`, chipset/USB topology, camera capabilities, board silkscreen, multimeter/logic analyzer, passive UART capture, and safe hardware inventory. Mọi capture phải có safety approval và không thay đổi GNSS configuration.
