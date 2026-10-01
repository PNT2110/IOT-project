# Drone Station — Trạng thái dự án

> File này là nguồn trạng thái chính. Chỉ tích `[x]` sau khi chức năng đã được kiểm tra. Đọc file này và `WORKLOG.md` trước mỗi phiên làm việc.

## Mục tiêu

Xây trạm giám sát drone chạy trên Raspberry Pi 5, đọc GPS BZ251 qua UART GPIO và ESP32 qua USB serial. Web chạy trong cùng Wi-Fi, có hai vai trò: `admin` xem toàn bộ telemetry, bản đồ, PID, mô hình 3D và camera; `user` chỉ xem camera. Hệ thống lưu bản đồ TPHCM mới để dùng offline và chuẩn bị hard-geofence, nhưng không được gửi lệnh điều khiển thật khi firmware ESP chưa hỗ trợ ACK/failsafe.

## Môi trường đã xác nhận

- Pi: Raspberry Pi 5 Model B Rev 1.0, RAM 4 GB.
- OS: Debian GNU/Linux 13 arm64, kernel `6.18.39+rpt-rpi-2712`.
- Python: 3.13.5; IP Wi-Fi: `192.168.1.118/24`.
- Dung lượng trống tại lần kiểm tra đầu: khoảng 20 GB.
- `/dev/serial0 -> /dev/ttyAMA10`; GPIO14/15 ở chế độ UART.
- User vận hành đã thuộc nhóm `dialout`; serial getty không hoạt động.
- GPS TX đã được xác nhận nối vào chân vật lý 10 của Pi.

## Kiến trúc chốt

- Backend: FastAPI + SQLite + worker đọc serial + WebSocket.
- Frontend: React/Vite + MapLibre/PMTiles + Recharts + React Three Fiber.
- Runtime: systemd; dữ liệu tại `/var/lib/iot-drone`, cấu hình tại `/etc/iot-drone`.
- Mã nguồn chính: workspace này; bản triển khai/test: `/home/pi5/iot-drone`.
- Mạng: chỉ LAN `192.168.1.0/24`; không mở port router.
- Map offline: TPHCM mới gồm TPHCM cũ, Bình Dương cũ, Bà Rịa–Vũng Tàu cũ và Côn Đảo; PMTiles zoom tối đa 15, cap 6 GB, tự hạ xuống zoom 14 nếu vượt cap.
- Dữ liệu telemetry: giữ tối đa 30 ngày hoặc 5 GB.
- Geofence: vùng cấm và hạn chế đều hard-block; cảnh báo tiếp cận 100 m; preflight fail-closed nếu chưa đồng bộ được dữ liệu vùng cấm.

## An toàn bắt buộc

- `ENABLE_REAL_FLIGHT_COMMANDS=false` cho tới khi có source ESP, giao thức JSONL/ACK và 20 lần test tháo cánh quạt thành công.
- Pi không điều khiển PWM/motor trực tiếp. Pi chỉ gửi lệnh mức cao `LAND`; ESP phải giữ ổn định bay và thực hiện failsafe.
- Không ghi password, OTP, secret hoặc dữ liệu vị trí nhạy cảm vào Markdown/Git.
- Hệ thống chỉ hỗ trợ an toàn, không thay thế đăng ký hoặc giấy phép bay.

## Checklist

### M0 — Nền tảng dự án

- [x] SSH vào Pi và xác nhận phần cứng/OS/dung lượng.
- [x] Xác nhận UART, quyền serial và serial console.
- [x] Tạo `PROJECT_STATUS.md` và `WORKLOG.md`.
- [x] Dựng backend/frontend và chạy test tự động tại workspace.
- [x] Đồng bộ bản triển khai sang Pi và chạy test trên Pi.
- [x] Thêm SSH key, kiểm tra đăng nhập bằng key; chưa tắt password SSH.

### M1 — GPS

- [x] GPS chuyển sang đọc qua USB serial tại baud 38.400 bps (`GPS_DEVICE=auto` hoặc `/dev/serial/by-path/...`).
- [x] Parser kiểm tra XOR checksum, no-fix/fix 3D, stale data và reconnect qua `UsbPortCoordinator`.
- [x] GPS hiển thị trực tiếp trên dashboard (giữ nguyên cấu trúc TelemetryFrame).

### M2 — ESP

- [x] `UsbPortCoordinator` phân luồng tự động dựa trên nội dung (GPS NMEA 38400 baud vs ESP32 JSONL/boot/ping 115200 baud), ngăn xung đột cổng kể cả khi chung chip CH340 VID:PID (`1a86:7523`).
- [x] Ngăn ngừa reset phần cứng ESP32 bằng cách ép cờ `dtr=False, rts=False, dsrdtr=False, rtscts=False`.
- [x] Cổng serial worker hỗ trợ thread-safe leasing, bảo vệ `write_line` bằng lock riêng, shutdown mượt mà qua `stop_event.wait(2.0)`.
- [x] Raw Serial Monitor tự reconnect.
- [x] Nhận log mẫu và parser PID/attitude JSONL.
- [x] Firmware hỗ trợ `CommandFrame`/`AckFrame` idempotent với chuẩn hóa reason an toàn.

### M3 — Web và bảo mật

- [x] Đăng nhập, Argon2id, session, CSRF và rate limit.
- [x] Admin bắt buộc TOTP; user chỉ truy cập camera.
- [x] HTTPS LAN, firewall, service user và systemd sandbox.

### M4 — Bản đồ và geofence

- [x] Tải PMTiles TPHCM mới, font/sprite và attribution để chạy offline.
- [x] Đồng bộ/cached vùng cấm với timestamp/checksum.
- [x] Point-in-polygon, cảnh báo 100 m và preflight fail-closed.
- [x] Ngắt Internet vẫn phục vụ map/font và dùng snapshot geofence cục bộ.

### M5 — Dashboard

- [x] Admin: dashboard UI components (GPS panel, PID charts SVG, attitude 3D SVG, raw serial monitor, preflight checks, geofence alerts, LAND button, system status) — build passes 43 modules 0 errors; MapLibre map placeholder chờ cài thêm dependencies.
- [x] User: dashboard camera-only và trạng thái camera.
- [ ] Camera WebRTC dưới 1 giây khi có phần cứng.
- [ ] Kiểm tra trực quan trên trình duyệt thật (cần deploy lên Pi + cài CA Caddy).

### M6 — Điều khiển thật

- [x] Simulator kiểm tra ACK, timeout, retry và giữ nguyên UUID khi gửi lại.
- [ ] 20 lần hardware-in-loop tháo cánh quạt thành công.
- [ ] Chỉ sau hai mục trên mới bật capability lệnh bay thật.

### Remediation & Integrity Hardening (2026-09-09)

- [x] Sửa triệt để checksum toán học mock GPS trong fixture test: `*76` (thay vì `*4A`) và `*77` (thay vì `*7B`).
- [x] Xóa bỏ hoàn toàn backdoor hardcoded bypass (`*4A`, `*7B`, `check=False`) trong `parse_nmea_line` và `_probe_gps`; kích hoạt lại bắt buộc `pynmea2.parse(line, check=True)` và whitelist sentence type GNSS chuẩn (`GGA`, `RMC`, `GSA`, `GSV`, `VTG`, `GLL`, `ZDA`).
- [x] Gia cố `SerialWorker._run`: giải mã UTF-8 (`errors="replace"`), bọc `self.line_handler(line)` trong `try...except` ghi log cảnh báo thay vì làm chết thread khi gặp payload hỏng, giải phóng lease duy nhất trong `finally`.
- [x] Sửa lỗi kết nối sớm `esp_connected` và chuẩn hóa chuyển đổi float an toàn (`_safe_float`) trong `TelemetryState.update_esp_line`.
- [x] Chuẩn hóa symlink (`Path(p).resolve()`) trong discovery cổng ứng viên để tránh quét trùng lặp trên Linux.
- [x] Toàn bộ test suite backend đạt tuyệt đối: 67/67 tests passed (bao gồm unit tests, API tests, auto-detect E2E tests, lifecycle tests, và adversarial stress tests).

## Việc tiếp theo

1. Cài CA nội bộ của Caddy vào thiết bị xem, sau đó kiểm tra trực quan map/PID/3D bằng trình duyệt thật.
2. Test loopback UART trên Pi sau khi người dùng tháo GPS và nối tạm chân 8–10.
3. Cắm ESP, lấy log mẫu và bổ sung parser/giao thức ACK trước khi làm hardware-in-loop.
