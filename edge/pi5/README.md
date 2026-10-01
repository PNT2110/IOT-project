# Trạm Pi 5

Web cục bộ trên Pi, phục vụ qua Wi-Fi do Pi phát (`http://192.168.4.1/`).

## Màn hình

1. **Kết nối Wi-Fi** — hiện khi Pi chưa có mạng ngoài: quét, chọn mạng, nhập mật khẩu.
2. **Đăng nhập / đăng ký** — mật khẩu + tích điều khoản → OTP mail → 2FA.
3. **User** — chỉ xem camera; nút "Xin quyền admin" trên thanh trên.
4. **Admin** — tab Camera, Bản đồ, Thông số, Người dùng, Firmware; nút "Xin cấp phép bay" trên thanh trên.

## Cấu trúc

| File | Nội dung |
|---|---|
| `pi5/web/asgi.py` | Nối phần cứng thật từ biến môi trường, chạy các vòng nền |
| `pi5/web/app.py` | App, đăng nhập, hồ sơ, vai trò, camera, bản đồ, telemetry |
| `pi5/web/extra_routes.py` | Wi-Fi, captive portal, stream camera, ô bản đồ, tinh chỉnh, firmware, đơn bay |
| `pi5/web/authority.py` | Gửi đơn bay lên máy chủ, hỏi kết quả, điều khiển quyền ARM của ESP32 |
| `pi5/web/device_crypto.py` | Phong bì AES-256-GCM (giống máy chủ) |
| `pi5/web/camera.py` | Webcam USB qua `v4l2-ctl`, một luồng MJPEG dùng chung |
| `pi5/web/firmware.py` | Lấy bản phát hành GitHub, kiểm SHA-256, nạp bằng esptool |
| `pi5/web/ui/` | Giao diện tĩnh; Leaflet và three.js nằm sẵn trong `vendor/` |
| `pi5/network/nm.py` | NetworkManager (`nmcli`) cho Wi-Fi ngoài |
| `pi5/telemetry/esp_link.py` | Chủ duy nhất của cổng serial ESP32, gửi `$PING` mỗi 2 giây |
| `pi5/telemetry/esp_command.py` | Dựng dòng lệnh có checksum |
| `pi5/cli.py` | `seed-default-admin`, `bootstrap-admin` |

## Biến môi trường

Xem `ops/pi5/pi.env.example`. Thiếu `PI_DEVICE_ID` / `PI_DEVICE_KEY` thì đơn
bay nằm ở trạng thái chờ gửi và ESP32 vẫn bị khóa.

## An toàn

- Pi chỉ cấp hoặc thu hồi *quyền* ARM. Không có lệnh ARM, DISARM hay quay motor.
- Mỗi lần khởi động và khi không có đơn được duyệt còn hiệu lực, Pi gửi `$AUTH,DENY`.
- Đổi PID, độ cao tối đa và nạp firmware đều bị từ chối khi drone đang ARM.
