# Drone Zone Check — F450 PNT PVD

Hệ thống vùng cấm bay cho drone, gồm ba phần: máy chủ trên PC, trạm Pi 5 gắn
trên drone và firmware ESP32. Đây là mô hình nghiên cứu của đồ án, không phải
cổng thông tin chính thức của cơ quan nhà nước; kết quả duyệt bay trong hệ
thống không thay thế giấy phép bay.

## Các cụm module

| Cụm | Thư mục | Việc chính |
|---|---|---|
| Máy chủ PC (API) | `server/` | Tài khoản, OTP mail, 2FA, hai cấp quyền, vùng cấm bay, duyệt bay, kênh thiết bị cho Pi |
| Web PC | `frontend/` | Bản đồ công khai, vẽ/sửa/xóa vùng, tab duyệt xin phép bay, tab duyệt tài khoản |
| Web Pi | `edge/pi5/pi5/web/` | Kết nối Wi-Fi, đăng nhập, camera, bản đồ, thông số, người dùng, firmware, xin phép bay |
| Mạng Pi | `edge/pi5/pi5/network/`, `ops/pi5/pi-network.sh` | Wi-Fi ngoài qua USB, captive portal |
| Pi ↔ ESP32 | `edge/pi5/pi5/telemetry/` | Đọc telemetry, gửi `$AUTH` / `$PID` / `$MAXALT` / `$PING` |
| Firmware | `firmware/FC_can_bang/` | Cân bằng, SBUS, GPS, khóa ARM theo cấp phép |
| Hợp đồng | `contracts/v1/` | Định dạng dữ liệu giữa các cụm |
| Vận hành | `ops/` | Script chạy máy chủ và triển khai Pi |

## Luồng xin phép bay

1. Admin trên Pi bấm "Xin cấp phép bay", điền họ tên, mã bằng lái, ngày, giờ, phương tiện.
2. Pi thêm vị trí GPS từ ESP32, mã hóa đơn bằng khóa riêng của Pi (AES-256-GCM) và gửi lên máy chủ.
3. Cán bộ duyệt hoặc từ chối trên web PC.
4. Pi hỏi kết quả. Được duyệt và đang trong giờ bay: Pi gửi `$AUTH,ALLOW` xuống ESP32. Còn lại: `$AUTH,DENY`.
5. ESP32 khởi động luôn ở trạng thái khóa. Không có lệnh ARM hay quay motor từ Pi hoặc PC; phi công vẫn ARM bằng công tắc trên tay điều khiển.

## Quyền

- Máy chủ: tài khoản chính (mặc định, 2FA cố định, không email), cấp 1 Admin (duyệt tài khoản, đổi cấp), cấp 2 (sửa vùng, duyệt bay). Khách chỉ xem bản đồ.
- Pi: user (chỉ xem camera, xin quyền admin) và admin. Tài khoản mặc định phải thêm email ở lần đăng nhập đầu.

## Chạy máy chủ trên PC

Cần Python 3.12, Node 20+, Tailscale. Điền `server/.env` (mẫu: `server/.env.example`), rồi:

```bash
powershell -ExecutionPolicy Bypass -File ops\pc\start-server.ps1
```

Script build web, chạy migration, tạo tài khoản chính nếu chưa có, rồi chạy API
(`127.0.0.1:8765`) và web (`127.0.0.1:5173`) ở nền. Dừng bằng
`ops\pc\stop-server.ps1`. Log ở `runtime\pc\`.

Công khai qua Tailscale Funnel:

```bash
tailscale funnel --bg 5173
```

Đăng ký một Pi (in ra `PI_DEVICE_ID` và `PI_DEVICE_KEY` một lần, cần các biến trong `server/.env`):

```bash
.venv\Scripts\python.exe -m server.cli add-device --name pitan
```

## Triển khai Pi

Cần SSH key từ PC vào Pi và file `ops/pi5/pi.env` đã điền (mẫu: `ops/pi5/pi.env.example`).

```bash
powershell -ExecutionPolicy Bypass -File ops\deploy-pi.ps1
```

Script chép `edge/pi5`, `firmware/FC_can_bang`, `contracts` lên `~/iot`, cài
service `iot-pi-web` ở cổng 80, tạo admin mặc định và build firmware. Thêm
`-Flash` để nạp firmware vào ESP32 (tháo cánh quạt trước). Captive portal:
`bash ~/iot/ops/pi5/pi-network.sh captive` trên Pi.

Phát hành firmware cho tab Firmware: xem `ops/release-firmware.md`.

## Kiểm thử

```bash
.venv\Scripts\python.exe -m pytest -q
```

```bash
npm --prefix frontend run typecheck
```

```bash
node --test tests/ops/static-server.test.mjs
```

`tests/firmware/` biên dịch và chạy logic khóa ARM và bộ đọc NMEA của firmware
trên máy tính (cần `g++`).

## Tài liệu

- Kế hoạch: `docs/superpowers/plans/2026-10-01-drone-zone-system.md`
- Hợp đồng: `contracts/v1/DEVICE_FLIGHT_CONTRACT.md`, `contracts/v1/SCOPE05_ESP32_USB_TELEMETRY_CONTRACT.md`
- Báo cáo cũ và lịch sử: `docs/reports/`, `archive/`
