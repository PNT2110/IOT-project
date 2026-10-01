# Báo cáo thực hiện — 2026-10-01

Trạng thái: **máy chủ đã công khai; web Pi đã chạy trên Pi thật ở cổng 8080;
firmware đã build được nhưng chưa nạp.** Phần phát Wi-Fi / captive portal / cổng
80 trên Pi chưa làm vì `sudo` trên Pi cần mật khẩu (mục 5).

## 0. Triển khai thật (2026-10-01)

| Hạng mục | Kết quả |
|---|---|
| Máy chủ PC | Chạy bằng `ops/pc/start-server.ps1`; tài khoản chính `pnt` đã tạo |
| Công khai | Funnel `/` → `127.0.0.1:5173`. Từ Internet: `/api/v1/health` 200 (production, PUBLIC), `/api/v1/public/zones` 200, `/api/v1/auth/me` 401, `/docs` 404. 9Router không còn công khai |
| Mail OTP | Đăng nhập SMTP Gmail thành công; chưa gửi thư nào (lần đăng nhập đầu của chủ dự án sẽ là lần thử thật) |
| Pi: web | Service người dùng `iot-pi-web` (systemd --user, tự chạy khi bật máy), `http://100.123.225.88:8080/`, health OK |
| Pi: tài khoản mặc định | Đã tạo `pitan` (admin, chưa có email) |
| Pi: camera USB thật | 20 khung JPEG liên tiếp, khoảng 18 khung/giây |
| Pi: bản đồ | Đồng bộ từ URL công khai thành công (hiện 0 vùng vì chưa vẽ vùng nào) |
| Pi → máy chủ (kênh mã hóa) | Máy chủ chấp nhận phong bì của Pi (trả 404 cho mã đơn không tồn tại, không phải 401) |
| Firmware | `arduino-cli compile` trên Pi thành công: 321 285 byte (24%), RAM 24 428 byte (7%). File ở `~/iot/firmware/build/FC_can_bang.bin` kèm `.sha256`. **Chưa nạp** |

Chưa làm được trên Pi:

- Đăng nhập thử trên web công khai và web Pi: cần mật khẩu của chủ dự án nên để chủ dự án tự thử.
- Cổng 80, phát Wi-Fi, captive portal: cần `sudo`. Hiện Pi vào mạng bằng dây (eth0), `wlan0` không kết nối, service `f450-ap` cũ ở trạng thái failed, **không thấy USB Wi-Fi** và **không thấy ESP32** (không có cổng serial CP210x).
- Tab Firmware: chưa có repo GitHub nên báo "chưa cấu hình kho firmware".

## 1. Kết quả kiểm thử (chạy trên PC này, 2026-10-01)

| Lệnh | Kết quả |
|---|---|
| `.venv\Scripts\python.exe -m pytest -q` | 206 passed |
| `npm --prefix frontend run typecheck` và `run build` | không lỗi |
| `node --test tests/ops/static-server.test.mjs` | 1 pass |
| `tests/firmware` (biên dịch `gps_nmea.h`, `flight_gate.h` bằng g++ rồi chạy) | 2 passed (nằm trong 206) |

Kiểm bằng trình duyệt trên bản chạy cục bộ (thư OTP ghi ra file, ESP32 và mạng của Pi là giả lập):

- Web PC: khách chỉ thấy bản đồ; tài khoản chính đăng nhập mật khẩu → 2FA (không OTP mail); vẽ hình chữ nhật và lưu vùng cấm bay.
- Web Pi: đăng nhập mật khẩu → OTP mail → 2FA; tab Thông số hiện độ cao, góc, pin, nhiệt độ, kênh tay điều khiển, mô hình 3D.
- Đầu-cuối: gửi đơn xin bay từ Pi → đơn (đã mã hóa) hiện ở tab duyệt trên web PC kèm vị trí GPS → bấm Duyệt → Pi hiện "Được phép bay" và gửi `$AUTH,ALLOW,3483,…` (trước đó là `$AUTH,DENY`).

## 2. Đối chiếu yêu cầu

Ký hiệu: **A** = có test tự động; **B** = đã kiểm bằng trình duyệt trên bản cục bộ; **C** = đã viết, chưa chạy trên thiết bị thật.

### Máy chủ PC

| Yêu cầu | Trạng thái |
|---|---|
| Chưa đăng nhập chỉ xem bản đồ và vùng cấm bay | A, B |
| Vẽ, sửa (kéo đỉnh), xóa vùng cấm bay và hạn chế bay | A (API), B (vẽ + lưu); kéo đỉnh và xóa chưa bấm thử |
| Tab duyệt xin phép bay (họ tên, bằng lái, ngày giờ, phương tiện, GPS) | A, B |
| Tab duyệt tài khoản (duyệt kèm chọn cấp, từ chối, đổi cấp, khóa) | A (API); giao diện chưa bấm thử |
| Đăng nhập: tài khoản + mật khẩu + tích điều khoản → OTP mail → 2FA | A |
| Đăng ký: tên, mail, mật khẩu ×2 → mã mail → khóa 2FA (bắt lưu) → chờ duyệt | A; giao diện chưa bấm thử |
| Tài khoản chính mặc định: 2FA mặc định, không xác nhận mail | A, B |
| Hai cấp: cấp 1 duyệt và nâng cấp; cấp 2 chỉ sửa vùng và duyệt bay | A |
| Công khai trên Internet | C — chưa chạy (chờ `server/.env`) |
| Gửi OTP bằng mail thật | C — chưa thử (chờ App Password) |

### Pi 5

| Yêu cầu | Trạng thái |
|---|---|
| Pi phát Wi-Fi liên tục, vào Wi-Fi tự mở web | C — route dò captive có test (A); cấu hình DNS trên Pi chưa chạy |
| Giao diện 1: kết nối Wi-Fi cho Pi qua USB | A (nmcli giả); chưa chạy trên Pi |
| Giao diện 2: đăng nhập / đăng ký, OTP mail, 2FA | A, B (đăng nhập) |
| Tài khoản mặc định phải thêm email ở lần đầu, sau đó luôn OTP mail | A |
| User / admin; đăng ký là user; chỉ admin nâng cấp | A |
| User chỉ xem camera, có nút xin quyền admin | A (quyền); stream camera thật chưa chạy |
| Admin: Camera, Bản đồ (chỉ xem, lấy từ máy chủ, có vị trí), Thông số + tinh chỉnh PID/độ cao + 3D, Người dùng, Firmware | A; B cho tab Thông số; bản đồ, camera, firmware chưa chạy với thiết bị thật |
| Xin cấp phép bay: mã hóa, gửi kèm GPS, nhận duyệt/từ chối | A, B |
| Duyệt → cho phép ARM; từ chối → tuyệt đối không ARM | A, B (ESP32 giả lập) |

### ESP32

| Yêu cầu | Trạng thái |
|---|---|
| GPS UART 38400, chân 16/17, NMEA 0183 v4.0/4.1 | A (bộ đọc NMEA trên máy); chưa build bằng arduino-cli, chưa nạp |
| Chỉnh nguyên lý mode bay cho khớp hệ thống | A (logic khóa ARM, mất Pi, giới hạn độ cao); chưa build, chưa nạp |

**Không nạp ESP32 lần này** theo quyết định của chủ dự án. Mọi thay đổi firmware mới chỉ được kiểm bằng test logic trên máy tính.

## 3. Thay đổi chính

- Máy chủ: tách `api.py` thành `app/routers/`; đăng nhập bằng tên tài khoản; tài khoản chính mặc định; mô hình hai cấp; kênh thiết bị `/api/v1/device/*`; sửa lỗi kẹt tài khoản khi bỏ dở bước 2FA.
- Web PC: vẽ/kéo sửa vùng bằng leaflet-geoman; tab duyệt bay có chi tiết và bản đồ GPS; tab duyệt tài khoản có chọn cấp, từ chối, khóa; mã QR cho khóa 2FA; điều khoản thật.
- Pi: giao diện tách ra file tĩnh; stream MJPEG; bản đồ Leaflet với ô bản đồ đi qua Pi; telemetry tự cập nhật; chỉnh PID và độ cao tối đa; người đang hoạt động; cập nhật firmware từ GitHub Releases; đơn bay lưu SQLite, tự gửi lại khi mất mạng.
- Firmware: `flight_gate.h` (khóa ARM, mất Pi 10 giây thì không ARM được, giới hạn độ cao hạ dần); GPS chỉ nghe, không kéo chân TX; lưu PID và độ cao tối đa vào NVS; đọc cờ failsafe của SBUS.

## 4. Quyết định đã tự đưa ra khi làm

- Giữ dòng "mô hình nghiên cứu — không phải cổng chính thức" trên trang công khai; không dùng tên hay logo thật của Bộ Quốc phòng.
- Xóa cơ chế ủy quyền chi tiết cũ (capability grant) vì trái với mô hình hai cấp.
- Đơn xin bay trên Pi chỉ dành cho admin (yêu cầu đặt nút ở phần admin).
- Quyền ARM chỉ mở trong khung giờ bay: từ giờ bay đã khai tới 60 phút sau.
- Trần ga khi vượt độ cao hạ 10 µs/giây (không phải 200 µs/giây) để máy bay không rơi đột ngột.
- Mật khẩu tài khoản mặc định cho phép từ 6 ký tự (do chủ dự án tự đặt); tài khoản đăng ký vẫn cần 12 ký tự.

## 5. Còn chờ chủ dự án

1. Đăng nhập thử: web công khai bằng `pnt`, web Pi bằng `pitan` (lần đầu Pi sẽ hỏi email).
2. Cho phép `sudo` trên Pi (hoặc tự chạy `bash ~/iot/ops/pi5/pi-setup.sh` trên Pi) để chuyển web sang cổng 80.
3. Cắm USB Wi-Fi và ESP32 vào Pi; quyết định cách phát Wi-Fi (service `f450-ap` cũ đang hỏng).
4. Tạo repo GitHub cho bản phát hành firmware rồi điền `PI_FW_GITHUB_REPO`.

## 6. Chưa làm

- Nạp firmware mới vào ESP32 và kiểm GPS, baro, khóa ARM trên phần cứng.
- La bàn I2C của module GPS; giao thức UBX (module phải đang xuất NMEA).
- Đo pin: chưa khai báo chân ADC nên % pin là rỗng.
- Tự chạy máy chủ khi bật máy PC.

## 7. Đã dọn

Xóa: `tools/`, `runtime/pi-sim/`, `ops/pi5/local_simulator.py`, `ops/pi5/README.md`, `ops/pc/run-windows-production.ps1`, `ops/pc/migrate.sh`, `ops/pc/restart.sh`, `frontend/src/styles (1).css`, giao diện Pi cũ (`pi-ui.css`, trang nhúng trong `app.py`), `tests/scope02/test_policy_amendment.py`, các `__pycache__`. Dừng hai tiến trình thử cũ ở cổng 4173 và 8082. Giữ bộ test hồi quy trong `tests/`.
