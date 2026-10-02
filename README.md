# Drone Zone Check — F450 PNT PVD

Hệ thống quản lý vùng cấm bay và cấp phép bay cho drone F450, gồm ba phần chạy
cùng nhau:

- **Máy chủ** trên PC: bản đồ vùng cấm bay công khai, nơi cán bộ vẽ vùng và
  duyệt đơn xin bay.
- **Trạm Pi 5** gắn trên drone: phát Wi-Fi, có web riêng để xem camera, thông
  số, bản đồ và gửi đơn xin bay.
- **Firmware ESP32** (bộ điều khiển bay): cân bằng, đọc GPS, và chỉ cho ARM khi
  đơn xin bay đã được duyệt.

Đây là mô hình nghiên cứu của đồ án (Phạm Ngọc Tấn, Phan Văn Đông). Nó không
phải cổng thông tin chính thức của cơ quan nhà nước, và kết quả duyệt bay trong
hệ thống không thay thế giấy phép bay của cơ quan có thẩm quyền.

## Mục lục

1. [Tổng quan kiến trúc](#tổng-quan-kiến-trúc)
2. [Luồng xin phép bay](#luồng-xin-phép-bay)
3. [Máy chủ PC](#máy-chủ-pc)
4. [Trạm Pi 5](#trạm-pi-5)
5. [Firmware ESP32](#firmware-esp32)
6. [Cấu trúc thư mục](#cấu-trúc-thư-mục)
7. [Cài đặt và chạy](#cài-đặt-và-chạy)
8. [Kiểm thử](#kiểm-thử)
9. [An toàn và bảo mật](#an-toàn-và-bảo-mật)
10. [Tình trạng hiện tại](#tình-trạng-hiện-tại)

## Tổng quan kiến trúc

```text
        Internet                         Wi-Fi "F450" (192.168.4.1)
           |                                      |
  Tailscale Funnel (HTTPS)               điện thoại / laptop
           |                                      |
+----------------------+   HTTPS, đơn   +----------------------+   USB serial   +------------------+
|  Máy chủ PC          | <------------- |  Trạm Pi 5           | <------------> |  ESP32 (FC)      |
|  FastAPI + SQLite    |  mã hóa AES-GCM|  FastAPI, cổng 80    |  115200 baud   |  IMU, baro, SBUS |
|  React + Leaflet     | -------------> |  camera USB, Wi-Fi   |  JSON / $lệnh  |  GPS, 4 ESC      |
+----------------------+  duyệt/từ chối +----------------------+                +------------------+
```

| Cụm | Thư mục | Việc chính |
|---|---|---|
| API máy chủ | `server/` | Tài khoản, OTP mail, 2FA, phân quyền, vùng cấm bay, duyệt bay, kênh thiết bị cho Pi |
| Web máy chủ | `frontend/` | Bản đồ công khai, vẽ/sửa/xóa vùng, tab duyệt xin phép bay, tab duyệt tài khoản |
| Web Pi | `edge/pi5/pi5/web/` | Chọn Wi-Fi, đăng nhập, camera, bản đồ, thông số, người dùng, firmware, xin phép bay |
| Mạng Pi | `edge/pi5/pi5/network/`, `ops/pi5/` | Wi-Fi phát luôn bật, Wi-Fi khách, captive portal |
| Pi ↔ ESP32 | `edge/pi5/pi5/telemetry/` | Đọc telemetry, gửi `$AUTH` / `$PID` / `$MAXALT` / `$PING` |
| Firmware | `firmware/FC_can_bang/` | Cân bằng, SBUS, GPS, baro, khóa ARM theo cấp phép |
| Hợp đồng dữ liệu | `contracts/v1/` | Định dạng trao đổi giữa các cụm |
| Vận hành | `ops/` | Script chạy máy chủ, triển khai Pi, cấu hình mạng Pi |

## Luồng xin phép bay

1. Admin trên web Pi bấm **Xin cấp phép bay**, điền họ tên, mã bằng lái, ngày
   bay, **bay từ giờ – đến giờ**, phương tiện. Họ tên và mã bằng lái được điền
   sẵn từ hồ sơ cá nhân trên Pi.
2. Pi lấy vị trí GPS hiện tại từ ESP32 (không có fix thì gửi "không có định
   vị"), mã hóa đơn bằng khóa riêng của Pi (AES-256-GCM) và gửi lên máy chủ.
   Mất mạng thì đơn nằm chờ và tự gửi lại.
3. Cán bộ mở tab **Duyệt xin phép bay** trên web máy chủ, xem thông tin và vị
   trí trên bản đồ, rồi bấm Duyệt hoặc Từ chối (từ chối phải ghi lý do).
4. Pi hỏi kết quả mỗi 5 giây:
   - Được duyệt **và** đang trong khoảng giờ bay đã xin → gửi `$AUTH,ALLOW`
     xuống ESP32.
   - Bị từ chối, chưa tới giờ, đã hết giờ, hoặc chưa có đơn → gửi `$AUTH,DENY`.
5. ESP32 chỉ cho ARM khi đang được phép và Pi còn gửi nhịp `$PING`. Phi công
   vẫn phải tự gạt công tắc ARM trên tay điều khiển.

Không có lệnh ARM, DISARM hay quay motor nào đi từ máy chủ hoặc từ Pi.

## Máy chủ PC

Chạy trên PC Windows, công khai qua Tailscale Funnel (HTTPS).

### Ai làm được gì

| Vai trò | Ý nghĩa | Quyền |
|---|---|---|
| Khách (chưa đăng nhập) | — | Chỉ xem bản đồ và các vùng công khai |
| `GUEST` | Vừa đăng ký | Chờ duyệt, chỉ xem bản đồ |
| `OPERATOR` | Cấp 2 | Vẽ/sửa/xóa vùng, duyệt xin phép bay |
| `ADMIN` | Cấp 1 | Như cấp 2, thêm duyệt tài khoản và đổi cấp |
| `OWNER` | Tài khoản chính | Mọi thứ; không ai đổi được tài khoản này |

### Đăng nhập và đăng ký

- **Đăng nhập:** tài khoản (tên hoặc email) + mật khẩu + tích đã đọc điều khoản
  → mã OTP gửi qua email → mã 2FA.
- **Đăng ký:** tên tài khoản, email, mật khẩu hai lần → mã xác nhận email →
  hiện khóa 2FA (kèm mã QR) và bắt lưu lại → chờ tài khoản chính hoặc Admin
  cấp 1 duyệt và chọn cấp.
- **Tài khoản chính mặc định:** tạo lúc khởi động từ `server/.env`, 2FA cố
  định, không có email nên bỏ qua bước OTP mail.
- Bỏ dở ở bước lưu khóa 2FA thì lần đăng nhập sau được cấp khóa mới.

### Các tab sau khi đăng nhập

- **Bản đồ & vùng cấm bay:** bản đồ OpenStreetMap (Leaflet). Vẽ đa giác hoặc
  chữ nhật, bấm vào vùng rồi kéo các đỉnh để sửa, xóa vùng. Mỗi vùng là "cấm
  bay" hoặc "hạn chế bay", công khai hoặc nội bộ.
- **Duyệt xin phép bay:** đơn từ các Pi, kèm họ tên, mã bằng lái, ngày giờ,
  phương tiện, thiết bị gửi và vị trí GPS trên bản đồ nhỏ.
- **Duyệt tài khoản** (cấp 1 và tài khoản chính): duyệt kèm chọn cấp, từ chối,
  đổi cấp, khóa và mở khóa.

### API chính (`/api/v1`)

| Nhóm | Đường dẫn | Ghi chú |
|---|---|---|
| Công khai | `GET /health`, `GET /public/zones` | Không cần đăng nhập |
| Xác thực | `/auth/register`, `/auth/login`, `/auth/verify-login-otp`, `/auth/verify-totp`, `/auth/mfa/*`, `/auth/me`, `/auth/logout` | Phiên bằng cookie + CSRF |
| Vùng | `/internal/zones` (GET, POST, PATCH, DELETE) | Cấp 2 trở lên, có kiểm tra phiên bản và ghi audit |
| Duyệt bay | `/flight-requests`, `/flight-requests/{id}/decision` | Cấp 2 trở lên |
| Tài khoản | `/account-review/users`, `.../status`, `.../role` | Cấp 1 trở lên |
| Thiết bị | `POST /device/flight-requests`, `POST /device/flight-requests/{id}/status` | Pi gọi, thân là phong bì mã hóa |

Chi tiết: [contracts/v1/README.md](contracts/v1/README.md),
[contracts/v1/DEVICE_FLIGHT_CONTRACT.md](contracts/v1/DEVICE_FLIGHT_CONTRACT.md).

## Trạm Pi 5

Pi có một chip Wi-Fi dùng cho hai việc cùng lúc: `ap0` **phát** Wi-Fi `F450`
(địa chỉ `192.168.4.1`) và `wlan0` **kết nối** vào Wi-Fi có Internet. Dây LAN
chỉ dùng lúc lập trình và thử; khi dùng thật sẽ rút ra, nên web chỉ coi Wi-Fi
là mạng của Pi.

### Trình tự màn hình

1. Vào Wi-Fi `F450` → điện thoại tự mở trang (captive portal), hoặc mở
   `http://192.168.4.1/`.
2. **Kết nối Wi-Fi cho F450:** hiện khi `wlan0` chưa kết nối mạng nào. Quét,
   chọn mạng, nhập mật khẩu. Lúc Pi nối mạng mới, Wi-Fi `F450` tắt-bật vài
   giây vì phải đổi kênh theo.
3. **Đăng nhập / đăng ký:** cùng luồng với máy chủ (mật khẩu + điều khoản →
   OTP email → 2FA). Tài khoản mặc định chưa có email nên lần đăng nhập đầu
   phải thêm email; các lần sau vẫn cần OTP email.
4. **Bảng điều khiển** theo vai trò.

### Vai trò trên Pi

| Vai trò | Thấy gì |
|---|---|
| `USER` (mọi tài khoản mới đăng ký) | Chỉ camera. Nút **Xin quyền admin** trên thanh trên cùng |
| `ADMIN` | Năm tab bên dưới và nút **Xin cấp phép bay** trên thanh trên cùng |

Bấm vào tên tài khoản trên thanh trên cùng để mở **Thông tin cá nhân**: họ tên,
mã bằng lái, hạng giấy phép, ngày hết hạn, email, đổi mật khẩu. Thay đổi được
xác nhận bằng mật khẩu hiện tại và OTP email.

### Các tab của admin

| Tab | Nội dung |
|---|---|
| Camera | Hình trực tiếp từ webcam USB (MJPEG qua `v4l2-ctl`) |
| Bản đồ | Vùng cấm bay lấy từ máy chủ (chỉ xem) và vị trí hiện tại của drone |
| Thông số | Độ cao baro, roll/pitch/yaw, % pin, nhiệt độ, 8 kênh tay điều khiển, mô hình 3D; chỉnh PID và độ cao tối đa |
| Người dùng | Ai hoạt động trong 5 phút gần đây; duyệt hoặc từ chối yêu cầu lên admin |
| Firmware | Bản phát hành mới nhất trên GitHub; kiểm SHA-256 rồi nạp ESP32 bằng esptool |

Chỉnh PID, đổi độ cao tối đa và nạp firmware đều bị từ chối khi drone đang ARM.

## Firmware ESP32

Mã ở `firmware/FC_can_bang/` (Arduino, ESP32 core 2.0.17, vòng điều khiển
200 Hz).

### Chân kết nối

| Chân | Dùng cho |
|---|---|
| GPIO 1 / 3 | USB serial tới Pi, 115200 baud |
| GPIO 5, 18, 19, 23 | IMU ICM20602 (SPI) |
| GPIO 21 / 22 | Baro BMP388 (I2C) |
| GPIO 16 (thử thêm 17) | GPS, UART1, 38400 baud, NMEA 0183 v4.0/4.1, chỉ nghe |
| GPIO 35 | Tay điều khiển SBUS |
| GPIO 27, 26, 25, 33 | ESC 1–4 |

### Nguyên lý mode bay

- Khởi động là **BLOCKED**. Mode gửi về Pi là một trong `BLOCKED`, `ANGLE`,
  `KILL`, `FAILSAFE`.
- ARM cần đủ, theo thứ tự ưu tiên: có tín hiệu tay điều khiển → Pi đã cho phép
  (`$AUTH,ALLOW` còn hạn) → Pi còn sống (`$PING` trong 10 giây) → công tắc mode
  ở ANGLE → công tắc ARM đã từng về vị trí tắt → ga thấp → gạt công tắc ARM.
  Lý do chưa ARM được hiện ở tab Thông số.
- Đang bay, chỉ ba thứ tắt motor: gạt DISARM, mất tay điều khiển (kể cả cờ
  failsafe của SBUS), gạt mode KILL. Hết phép hoặc mất Pi giữa chuyến **không**
  cắt motor; nó chỉ chặn lần ARM kế tiếp.
- Vượt độ cao tối đa (so với điểm cất cánh): trần ga bị chốt rồi hạ dần
  10 µs/giây cho tới khi máy bay thấp hơn trần 1 m.
- PID và độ cao tối đa do Pi gửi được lưu vào bộ nhớ của ESP32.

### Trao đổi với Pi

- ESP32 → Pi: mỗi 200 ms một dòng JSON (góc, baro, pin, nhiệt độ, kênh SBUS,
  GPS, trạng thái bay, PID).
- Pi → ESP32: dòng lệnh có checksum kiểu NMEA — `$AUTH,ALLOW,<giây>,<mã đơn>`,
  `$AUTH,DENY,<mã đơn>`, `$PID,<trục>,<kp>,<ki>,<kd>`, `$MAXALT,<mét>`, `$PING`.

Chi tiết: [contracts/v1/SCOPE05_ESP32_USB_TELEMETRY_CONTRACT.md](contracts/v1/SCOPE05_ESP32_USB_TELEMETRY_CONTRACT.md).

## Cấu trúc thư mục

```text
server/                 API máy chủ (FastAPI, SQLAlchemy, Alembic)
  app/routers/          auth, zones, accounts, flights, device, misc
  app/device_crypto.py  phong bì AES-256-GCM cho kênh thiết bị
  cli.py                seed-default-owner, add-device
  migrations/           lược đồ cơ sở dữ liệu
frontend/               web máy chủ (React, TypeScript, Vite, Leaflet)
edge/pi5/pi5/
  web/                  app Pi, đăng nhập, camera, firmware, đơn bay
  web/ui/               giao diện Pi (HTML/CSS/JS thuần, Leaflet và three.js kèm sẵn)
  network/nm.py         điều khiển Wi-Fi khách qua NetworkManager
  telemetry/            đọc ESP32, dựng lệnh, giữ kết nối serial
firmware/FC_can_bang/   firmware ESP32
firmware/build/         file .bin đã build và mã SHA-256
contracts/v1/           hợp đồng dữ liệu giữa các cụm
ops/pc/                 start-server.ps1, stop-server.ps1, static-server.mjs
ops/pi5/                pi-setup.sh, pi-network.sh, pi-wifi-permission.sh, pi.env.example
ops/deploy-pi.ps1       đóng gói và triển khai lên Pi
ops/release-firmware.md cách đăng bản phát hành firmware
tests/                  kiểm thử tự động
docs/                   kế hoạch, yêu cầu, báo cáo
archive/                mã và tài liệu cũ, chỉ để tra cứu
```

## Cài đặt và chạy

### Máy chủ (PC Windows)

Cần Python 3.12, Node.js 20 trở lên, Tailscale.

1. Tạo môi trường và cài thư viện:

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python.exe -m pip install -r server\requirements.lock
```

```bash
npm --prefix frontend ci
```

2. Chép `server/.env.example` thành `server/.env` và điền: `PUBLIC_HOST`,
   `SESSION_SECRET`, thông tin SMTP (Gmail thì dùng App Password), và ba dòng
   `DEFAULT_OWNER_*` cho tài khoản chính.

3. Chạy:

```bash
powershell -ExecutionPolicy Bypass -File ops\pc\start-server.ps1
```

   Script build web, cập nhật cơ sở dữ liệu, tạo tài khoản chính nếu chưa có,
   rồi chạy API (`127.0.0.1:8765`) và web (`127.0.0.1:5173`) ở nền. Log nằm ở
   `runtime\pc\`. Dừng bằng `ops\pc\stop-server.ps1`.

4. Công khai ra Internet:

```bash
tailscale funnel --bg 5173
```

5. Đăng ký một Pi (in ra `PI_DEVICE_ID` và `PI_DEVICE_KEY` một lần; cần các
   biến trong `server/.env` đã nạp vào môi trường):

```bash
.venv\Scripts\python.exe -m server.cli add-device --name pitan
```

### Pi 5

Cần Raspberry Pi OS có NetworkManager, SSH key từ PC vào Pi, webcam USB.

1. Chép `ops/pi5/pi.env.example` thành `ops/pi5/pi.env` và điền: SMTP, tài
   khoản admin mặc định, `PI_PC_MAP_URL` (địa chỉ máy chủ), `PI_DEVICE_ID`,
   `PI_DEVICE_KEY`, `PI_FW_GITHUB_REPO`.

2. Triển khai từ PC (chép mã lên `~/iot`, cài service web cổng 80, build
   firmware; thêm `-Flash` để nạp ESP32, nhớ tháo cánh quạt trước):

```bash
powershell -ExecutionPolicy Bypass -File ops\deploy-pi.ps1
```

3. Cài phần phát Wi-Fi và captive portal, chạy trên Pi một lần (cần sudo):

```bash
bash ~/iot/ops/pi5/pi-network.sh install
```

Sau đó Pi tự chạy web và tự phát Wi-Fi mỗi khi có điện (`iot-pi-web`,
`f450-ap`).

### Phát hành firmware

Tab Firmware trên Pi đọc bản phát hành mới nhất của repo ghi trong
`PI_FW_GITHUB_REPO` và cần hai file đính kèm: `FC_can_bang.bin` và
`FC_can_bang.bin.sha256`. Cách build và đăng: [ops/release-firmware.md](ops/release-firmware.md).

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

| Thư mục | Kiểm gì |
|---|---|
| `tests/scope01`, `tests/scope02` | Đăng nhập, vùng, tài khoản, phân quyền, duyệt bay trên máy chủ |
| `tests/scope03` | Điều khiển Wi-Fi của Pi (nmcli giả) |
| `tests/scope04` | Web Pi: đăng nhập, quyền, camera, tinh chỉnh, mạng |
| `tests/scope05` | Phân tích telemetry và dựng lệnh ESP32 |
| `tests/scope06` | Kênh mã hóa Pi → máy chủ, đơn bay và quyền ARM |
| `tests/scope07` | Cập nhật firmware |
| `tests/firmware` | Biên dịch và chạy logic khóa ARM, bộ đọc NMEA trên máy tính (cần `g++`) |

## An toàn và bảo mật

- Trước khi nạp firmware hoặc thử ARM trên bàn: **tháo cánh quạt**.
- Mật khẩu băm bằng Argon2; khóa 2FA và thông tin đơn bay được mã hóa khi lưu.
- Mỗi Pi có khóa riêng; máy chủ từ chối gói bị sửa, gói gửi lại, hoặc lệch
  giờ quá 5 phút.
- `server/.env` và `ops/pi5/pi.env` chứa bí mật và không được đưa lên git.
- Wi-Fi `F450` không dùng HTTPS; chỉ nên dùng mật khẩu Wi-Fi đủ mạnh khi bay
  thật, vì màn hình chọn Wi-Fi mở cho mọi máy đã vào được `F450`.

## Tình trạng hiện tại

Đã chạy thật:

- Máy chủ công khai qua Tailscale Funnel; vẽ vùng và duyệt đơn bay.
- Web Pi ở cổng 80, tự chạy khi Pi khởi động; Wi-Fi `F450` phát cả khi Pi
  chưa kết nối mạng nào; Pi kết nối được Wi-Fi ngoài.
- Camera USB trên Pi; đồng bộ bản đồ và gửi đơn bay từ Pi lên máy chủ.
- Firmware build được bằng `arduino-cli` (file ở `firmware/build/`).

Chưa kiểm trên phần cứng:

- Firmware mới chưa nạp vào ESP32: GPS, khóa ARM và giới hạn độ cao mới chỉ
  qua kiểm thử logic trên máy tính.
- Chưa có bản phát hành firmware trên GitHub nên tab Firmware chưa có gì để tải.

Chưa làm:

- La bàn I2C của module GPS và giao thức UBX (module phải đang xuất NMEA).
- Đo pin: chưa khai báo chân ADC nên % pin để trống.
- Máy chủ tự chạy khi bật máy PC.

Báo cáo chi tiết: [docs/reports/FINAL_DEPLOY_REPORT_2026-10-01.md](docs/reports/FINAL_DEPLOY_REPORT_2026-10-01.md).
