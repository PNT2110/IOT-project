# Báo cáo đối chiếu yêu cầu + firmware GPS — 2026-10-01

Kiểm tra theo yêu cầu gốc của chủ dự án (server PC "bộ quốc phòng", web Pi 5,
firmware ESP32 FC_can_bang + GPS). Báo cáo phân biệt rõ **đã kiểm chứng**,
**đã viết nhưng chưa thử trên phần cứng**, và **chưa có**.

> Giới hạn của phiên này: chỉ đọc/ghi được file trong thư mục `IOT` trên PC,
> **không có shell trên PC và không SSH được tới Pi**, nên **chưa nạp firmware,
> chưa deploy lên Pi, chưa chạy test trên phần cứng**. Build và test chạy trong
> môi trường cloud với toolchain ESP32 Arduino core 2.0.17 và mã nguồn Pi thật.

## 1. Chia module (để phát triển độc lập)

| Cụm | Thư mục | Trách nhiệm | Giao tiếp với |
|---|---|---|---|
| M1 PC API | `server/app` | Tài khoản, OTP mail, TOTP, RBAC Owner/Admin/Operator, vùng cấm bay, duyệt bay, audit | M2 (REST), M3 (`/api/v1/public/zones`, `/api/v1/pi/v1/*`) |
| M2 PC Web | `frontend/` | Bản đồ công khai, vẽ/sửa/xóa vùng, tab duyệt bay, tab duyệt tài khoản | M1 |
| M3 Pi Web | `edge/pi5/pi5/web` | Đăng nhập/đăng ký Pi, camera USB, bản đồ cache, telemetry/3D, xin cấp phép bay, quản trị | M1 (HTTPS), M5 |
| M4 Pi Network | `edge/pi5/pi5/network` + `ops/pi5` | AP luôn phát, captive portal, giao diện 1 (kết nối Wi‑Fi) | M3 |
| M5 Pi↔ESP link | `edge/pi5/pi5/telemetry` | Đọc frame JSON từ ESP; gửi lệnh `$AUTH/$PID/$MAXALT/$PING` | M6 (USB 115200) |
| M6 Firmware ESP32 | `firmware/FC_can_bang` (**mới, bản đang dùng**) | Cân bằng, SBUS, ESC, GPS, baro, khóa ARM, telemetry | M5 |
| Hợp đồng | `contracts/v1` | Định dạng dữ liệu giữa các cụm | tất cả |

Bản gốc của firmware vẫn giữ nguyên trong `archive/firmware/FC_can_bang.zip`.

## 2. Đối chiếu từng yêu cầu

Ký hiệu: ✅ có và đã test tự động · 🟡 có nhưng chưa kiểm chứng thật (phần cứng/mail/production) · ❌ chưa có

### Server PC (web bộ quốc phòng)

| Yêu cầu | Trạng thái | Ghi chú |
|---|---|---|
| Web công khai | 🟡 | Đang chạy qua Cloudflare quick tunnel (URL tạm). Bản public **cũ hơn** bản trong máy (thiếu link điều khoản). |
| Chưa đăng nhập chỉ xem map + vùng cấm bay | ✅ | `/api/v1/public/zones`; các API khác trả 401. Hiện **0 vùng** được công bố. |
| Map kiểu Google Maps, vẽ/xóa/sửa vùng cấm & hạn chế bay | ✅ | Leaflet/OSM, GeoJSON, có version guard + audit. |
| Tab duyệt xin phép bay | ✅ | `/flight-requests/*/review|decision` (đang gắn nhãn "mô phỏng"). |
| Tab duyệt tài khoản | ✅ | `/account-review/*`. |
| Đăng nhập: tài khoản + pass + tích điều khoản → OTP mail → 2FA | ✅/🟡 | Logic + test có; **chưa có SMTP thật** nên chưa thử mail thật. |
| Đăng ký: tên, mail, pass ×2 → mã mail → 2FA (bắt lưu mã) | ✅/🟡 | Có recovery codes; sau đăng ký phải đăng nhập lại. |
| Tài khoản chính đầu tiên: 2FA mặc định, không xác nhận mail | 🟡 **lệch** | Code hiện tại bootstrap Owner bằng CLI và **vẫn yêu cầu mail + TOTP thật** (vì lý do bảo mật). Nếu bạn vẫn muốn "2FA mặc định", cần quyết định lại — khuyến nghị giữ như hiện tại. |
| Người đăng ký chờ tài khoản chính duyệt; 2 cấp: Admin (duyệt + nâng cấp) và cấp 2 (sửa vùng + duyệt bay) | ✅ | Owner/Admin/Operator trong RBAC. |
| Nguồn vùng cấm bay chính thức | ❌ | `cambay.mod.gov.vn` chưa có API máy-máy được phép dùng; không cào dữ liệu. |

### Web trên Pi 5

| Yêu cầu | Trạng thái | Ghi chú |
|---|---|---|
| Pi phát Wi‑Fi liên tục + tự mở web (captive portal) | ❌ trên Pi thật | Kiểm kê Pi: **không có hostapd/dnsmasq/service web**. Code mạng có ở dạng mô phỏng. |
| Giao diện 1: chưa có Internet → trang kết nối Wi‑Fi cho Pi | 🟡 | Có model/adapter, chưa chạy trên Pi. |
| Giao diện 2: bắt buộc đăng nhập/đăng ký, OTP mail + 2FA | ✅ (giả lập) | 53 test Pi pass trong lần chạy này. |
| Tài khoản mặc định: lần đầu phải nhập email, sau đó luôn OTP mail | ✅ | `/auth/email/setup`, có test. |
| User/Admin; đăng ký mặc định là User; chỉ Admin nâng cấp | ✅ | |
| User: chỉ xem webcam USB; nút xin quyền Admin trên thanh trên | ✅ (giả lập) | Webcam `/dev/video0` có trên Pi (1920×1080 MJPG) nhưng chưa test web stream trên Pi. |
| Admin tab 1 webcam, tab 2 map + vị trí (lấy vùng từ PC, chỉ xem) | 🟡 | Đồng bộ map HTTPS từ PC có; vị trí GPS nay có từ ESP (xem mục 3). |
| Tab thông số drone: độ cao baro, góc nghiêng, % pin, nhiệt độ, tín hiệu tay điều khiển, mô hình 3D | 🟡 | Firmware nay gửi đủ (pin = null cho tới khi khai báo chân ADC). UI Pi đã có tab telemetry/3D. |
| Tinh chỉnh độ cao tối đa, PID | 🟡 | Firmware + lệnh Pi→ESP đã có và đã test; **chưa có nút trên UI Pi** (endpoint admin cần thêm vào `web/app.py`). |
| Tab ai đang hoạt động + duyệt lên Admin | ✅ | |
| Tab cập nhật FW từ nhà sản xuất | ❌ | Chỉ có trang trạng thái; nạp firmware đang khóa (cần manifest ký số + rollback). |
| Form xin phép bay: họ tên, mã bằng lái, ngày, giờ, phương tiện | ✅ | Có thêm GPS. |
| Mã hóa + gửi kèm GPS lên server PC, PC duyệt/từ chối trả về Pi | ❌ | **Thiếu kênh thiết bị Pi→PC** (Pi đang ghi `PC_AUTHORITY_ADAPTER_NOT_CONFIGURED`). Đây là lỗ hổng lớn nhất còn lại. |
| Duyệt → gửi lệnh xuống ESP; từ chối → ESP tuyệt đối không ARM | ✅ phía ESP/Pi | `EspFlightAuthorizationBridge` + khóa ARM trong firmware (test bên dưới). Chỉ còn nối với kênh PC ở dòng trên. |

### ESP32 (FC_can_bang) + GPS — đã làm trong phiên này

| Yêu cầu | Trạng thái |
|---|---|
| Thêm GPS UART 38400, chân 16/17, NMEA 0183 v4.0/4.1 | ✅ build + test parser. Firmware **tự dò** chân RX (16 rồi 17) vì chưa chắc dây TX của GPS cắm chân nào. Chỉ đọc, không gửi UBX cấu hình. |
| Sửa nguyên lý mode bay (chỉ phần mode/ARM) | ✅ build + test logic | PID, bộ lọc, trộn motor giữ nguyên. |
| Gửi thông số cho Pi | ✅ | Frame JSON khớp đúng parser hiện có của Pi (đã kiểm bằng `parse_esp_frame`). |

## 3. Thay đổi firmware (`firmware/FC_can_bang`)

| File | Nội dung |
|---|---|
| `gps_nmea.h` (mới) | Parser GGA/RMC mọi talker (GP/GN/…), bắt buộc checksum; parser lệnh `$...*HH`. |
| `GPS.ino` (mới) | `HardwareSerial(1)` 38400 8N1, tự dò RX 16↔17, giới hạn 128 byte/vòng để không trễ vòng 5 ms, STALE sau 2 s. |
| `Baro.ino` (mới) | BMP388 I2C (SDA21/SCL22, 0x76/0x77), bù trừ theo datasheet, độ cao tương đối điểm khởi động + vận tốc đứng. Không thấy cảm biến → gửi `null`. |
| `Power.ino` (mới) | Đo pin qua ADC — **mặc định tắt** (`BATTERY_ADC_PIN -1`) vì chưa có sơ đồ chân; khai báo chân + tỉ lệ cầu phân áp để bật. |
| `Link.ino` (mới) | Telemetry 5 Hz qua USB 115200, không bao giờ chặn vòng điều khiển; nhận lệnh `$AUTH/$PID/$MAXALT/$PING`. |
| `FC_can_bang.ino` | Máy trạng thái ARM mới (dưới). Gọi SBUS 1 lần/vòng (bản cũ gọi 2 lần). |
| `MODE.ino` | `no_fly()` không còn tự đặt `status_arm=0` (bản cũ gây ARM/DISARM nhấp nháy mỗi vòng). Thêm giới hạn độ cao tối đa. |
| `ICM20602.ino` | Nhiệt độ IMU, yaw tương đối (tích phân gyro), buffer TX 2 KB, bỏ dòng in "calib thanh cong" làm hỏng frame. |

**Điều kiện ARM mới** (tất cả phải đúng): tín hiệu RC hợp lệ · **Pi đã gửi `$AUTH,ALLOW` còn hạn** · công tắc mode ở ANGLE · công tắc ARM đã từng ở DISARM (không ARM ngay khi bật nguồn) · ga thấp. Lý do bị chặn hiện ở `flight.arm_block_reason`.

**Khi đang bay:** gạt DISARM, mất RC >200 ms hoặc gạt mode khác ANGLE → tắt motor (giữ như bản gốc). Lệnh `$AUTH,DENY` khi đang bay **không cắt motor giữa không trung** (sẽ làm rơi máy) mà chặn lần ARM sau. Pi **không có lệnh ARM/quay motor**; quyền ARM chỉ nằm trong RAM — ESP khởi động lại là bị khóa cho đến khi Pi cấp lại.

Tùy chọn `REQUIRE_GPS_FIX_TO_ARM` (mặc định 0 để còn thử trong nhà).

## 4. Kết quả kiểm thử (phiên này)

| Kiểm thử | Kết quả |
|---|---|
| Build firmware gốc (ESP32 Arduino core 2.0.17, esp32dev) | PASS — 279 217 byte |
| Build firmware mới | PASS — 312 661 byte flash (23%), 24 388 byte RAM (7%); SHA-256 `b3fc3c6e…6092628b` |
| Test host logic firmware: parser NMEA (fix, tọa độ, độ cao, sai checksum, RMC V/A), khóa ARM (chưa cấp phép, công tắc chưa reset, ga cao, sai mode, ARM thành công, DENY giữa chuyến không cắt motor, hết hạn, mất RC failsafe), PID/MAXALT bị từ chối khi ARM, checksum sai, tham số ngoài khoảng | 0 lỗi |
| Lệnh do Python (Pi) tạo → đưa vào mã C++ của firmware | PASS (4/4 lệnh được chấp nhận) |
| Frame do firmware tạo → `parse_esp_frame` của Pi | PASS |
| Pytest Pi `tests/scope04` + `tests/scope05` | 66 passed (53 cũ + 13 mới/sửa) |

**Chưa kiểm thử:** nạp ESP thật, GPS thật, BMP388 thật, đo vòng lặp 5 ms trên chip, bất cứ thứ gì trên Pi thật, mail SMTP thật, luồng PC↔Pi.

Thay đổi hợp đồng Pi có chủ đích: Pi giờ đọc **frame mới nhất** và đếm frame bị bỏ (`dropped_frames`) thay vì báo lỗi `SEQUENCE_GAP`; ESP khởi động lại (uptime giảm) không còn bị coi là replay. Test `test_usb_web_source_rejects_sequence_gaps` được đổi tương ứng.

## 5. Cách nạp và thử (khi có quyền truy cập Pi)

Trên Pi (ESP cắm USB CP2102), với tháo cánh quạt:

```bash
arduino-cli compile -b esp32:esp32:esp32 firmware/FC_can_bang      # core esp32 2.0.x (dùng ledcSetup)
arduino-cli upload  -b esp32:esp32:esp32 -p /dev/serial/by-id/usb-Silicon_Labs_CP210* firmware/FC_can_bang
python3 -c "import serial;s=serial.Serial('/dev/ttyUSB0',115200);[print(s.readline()) for _ in range(5)]"
```

Kiểm tra trên frame: `gnss.detected=true`, `gnss.uart_rx_pin` (16 hoặc 17), `fix_state` → `VALID_FIX` ngoài trời, `baro.available`, `flight.arm_state=BLOCKED` khi chưa cấp phép.

## 6. Việc còn lại (theo thứ tự ưu tiên)

1. **Kênh thiết bị Pi→PC cho xin phép bay**: Pi đăng ký thiết bị (khóa/khóa API riêng), gửi đơn đã mã hóa + GPS tới PC qua HTTPS; PC duyệt; Pi nhận kết quả (poll) → `EspFlightAuthorizationBridge.apply_decision(...)` và gọi `refresh()` ~30 s/lần.
2. Thêm endpoint admin (CSRF + RBAC) trên Pi cho PID/độ cao tối đa dùng `esp_command.set_pid/set_max_altitude`, mở `UsbSerialLineReader(allow_commands=True)`.
3. Cấu hình SMTP thật cho PC và Pi; bootstrap Owner.
4. Cài AP + captive portal + service web trên Pi (hostapd/dnsmasq hoặc NetworkManager), chứng chỉ HTTPS.
5. Khai báo chân đo pin; xác nhận cảm biến baro thật trên mạch.
6. Tab cập nhật firmware: manifest có chữ ký + rollback trước khi mở quyền nạp.
7. Deploy lại bản PC mới lên public; đổi quick tunnel sang domain cố định; khóa cổng 9Router (20128) đang mở mọi interface.

## 7. Dọn dẹp

Toàn bộ file test tạm (harness C++, frame mẫu, build output, bản copy) chỉ nằm
trong môi trường cloud và không ghi vào thư mục dự án. Trong dự án chỉ thêm mã
nguồn, test hồi quy chính thức (`tests/scope05/test_esp_command.py`) và báo cáo này.
