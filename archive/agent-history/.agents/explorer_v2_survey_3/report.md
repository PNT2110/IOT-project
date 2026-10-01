# BÁO CÁO KHẢO SÁT CHUYÊN SÂU: FRONTEND, MOD SERVER & TỰ ĐỘNG HÓA KIỂM THỬ SSH (v2)

**Chuyên viên khảo sát**: Explorer 3 (Frontend, MOD Server & Automated Test Specialist)  
**Ngày thực hiện**: 13/09/2026  
**Thư mục làm việc**: `/home/pnt/IOT/.agents/explorer_v2_survey_3`  
**Tài liệu đặc tả**: `/home/pnt/IOT/prompt-du-an-drone-v2.md` (Mục 5, 6, 7, 8, 9, 11, 12)  
**Mục tiêu**: Khảo sát hiện trạng frontend `/home/pnt/IOT/frontend`, thiết kế kiến trúc máy chủ Bộ Quốc Phòng (MOD Server), và xây dựng kế hoạch kiểm thử tự động toàn diện cho 16 kịch bản SSH (Bảng 12.1).

---

## MỤC LỤC
1. [TỔNG QUAN HIỆN TRẠNG & PHÁT HIỆN TRỌNG TÂM](#1-tổng-quan-hiện-trạng--phát-hiện-trọng-tâm)
2. [KHẢO SÁT & KẾ HOẠCH NÂNG CẤP FRONTEND 6 TABS](#2-khảo-sát--kế-hoạch-nâng-cấp-frontend-6-tabs)
   - 2.1 Cấu trúc mã nguồn hiện tại (`frontend/src`)
   - 2.2 So sánh cấu trúc Tab hiện tại vs 6 Tab yêu cầu
   - 2.3 Chi tiết thiết kế từng Tab & Khoảng trống kỹ thuật (Gaps)
   - 2.4 Modal & Nút "Xin phép bay" trên Header
   - 2.5 Phân quyền giao diện theo Role & Gatekeeper lần đầu
3. [ĐẶC TẢ HỆ THỐNG THIẾT KẾ THEME XANH — TRẮNG (BLUE-WHITE)](#3-đặc-tả-hệ-thống-thiết-kế-theme-xanh--trắng-blue-white)
   - 3.1 Đánh giá phong cách giao diện hiện tại
   - 3.2 Bảng mã màu & Design Tokens (Blue-White Aviation GCS)
   - 3.3 Quy chuẩn giao diện Captive Portal ESP32 & Web Pi5
4. [THIẾT KẾ TOÀN DIỆN MÁY CHỦ BỘ QUỐC PHÒNG (MOD SERVER)](#4-thiết-kế-toàn-diện-máy-chủ-bộ-quốc-phòng-mod-server)
   - 4.1 Kiến trúc hệ thống & Ngăn xếp công nghệ
   - 4.2 Thiết kế cơ sở dữ liệu (Schema & Entities)
   - 4.3 Đặc tả API Contracts (Pi5 ⇄ MOD Server & Admin MOD UI)
   - 4.4 Thuật toán Geofencing động (Bán kính 1km & Tự động hết hạn)
   - 4.5 Cơ chế chống tấn công phát lại (Anti-Replay) & Bảo mật kết nối
5. [CHI TIẾT 16 KỊCH BẢN KIỂM THỬ SSH TỰ ĐỘNG (BẢNG 12.1)](#5-chi-tiết-16-kịch-bản-kiểm-thử-ssh-tự-động-bảng-121)
   - 5.1 Bảng chi tiết 16 kịch bản kiểm thử (Mục tiêu, Phương pháp, Kỳ vọng)
   - 5.2 Kiến trúc Test Harness tự động qua SSH (Paramiko Runner)
   - 5.3 Môi trường giả lập Mock Fixtures (ESP32 PTY, Fake GPS NMEA, Camera, Mock MOD)
   - 5.4 Hiện trạng kết nối Pi5 thực tế & Khắc phục lỗi SyntaxError phát hiện
6. [LỘ TRÌNH TRIỂN KHAI & ĐỀ XUẤT CHO CÁC NHÓM KỸ THUẬT](#6-lộ-trình-triển-khai--đề-xuất-cho-các-nhóm-kỹ-thuật)

---

## 1. TỔNG QUAN HIỆN TRẠNG & PHÁT HIỆN TRỌNG TÂM

### 1.1 Những phát hiện then chốt từ thực tế mã nguồn và phần cứng:
1. **Kết nối SSH Pi5 thực tế**: Máy trạm Raspberry Pi 5 tại địa chỉ IP `192.168.1.118` (user `pi5`, port 22) **đang hoạt động trực tuyến** (ping ~2.3ms, SSH kết nối thành công qua Paramiko).
2. **Dịch vụ đang chạy trên Pi5**: `drone-web-ui.service` đang chạy dưới `/opt/drone-web-ui/venv/bin/uvicorn app.main:app --port 8000`. Log cho thấy USB Camera thực tế đang cắm và truyền dữ liệu video.
3. **Môi trường Python trên Pi5**: Thư mục venv `/opt/iot-drone/venv` được trang bị đầy đủ các thư viện phụ thuộc (`fastapi`, `pyserial`, `pynmea2`, `shapely`, `argon2-cffi`, `pyotp`, `pytest`). Bộ test có thể kích hoạt trực tiếp từ xa bằng SSH: `PYTHONPATH=. /opt/iot-drone/venv/bin/pytest`.
4. **Lỗi cú pháp blocker nghiêm trọng trong `backend/app/main.py`**:
   - Dòng 68 chứa chuỗi ký tự gãy dòng sai cú pháp: `gps_lost_since: float | None = None\n    global GLOBAL_FLIGHT_PERMISSION\n    flight_permission = GLOBAL_FLIGHT_PERMISSION` khiến Python báo lỗi `SyntaxError: unexpected character after line continuation character`.
   - Dòng 147 khai báo decorator sai: `@app.post("/api/v1/auth/login", response_model=LoginResponse, SetupRequest)`.
   - Lỗi này làm gãy quá trình load test `test_api.py` cả trên local lẫn trên Pi5. Cần sửa khẩn cấp khi bước vào giai đoạn thực thi.
5. **Hiện trạng Frontend**:
   - Sử dụng React 19 (`19.1.1`), TypeScript (`5.9.2`), Vite (`7.1.3`), MapLibre GL (`5.7.1`), PMTiles (`4.3.0`), Three.js (`0.179.1`), Recharts (`3.1.2`).
   - Bộ công cụ Node.js v20.11.1 và npm 10.2.4 nằm tại `/home/pnt/IOT/node-v20.11.1-linux-x64/bin`. Lệnh `export PATH="/home/pnt/IOT/node-v20.11.1-linux-x64/bin:$PATH" && npm run build` biên dịch thành công (bundle 2.6MB, CSS 82KB).
   - Giao diện hiện tại mang phong cách **Cyberpunk tối màu** (nền `#04090c`, panel `#081216`, điểm nhấn xanh neon `#35e6c1`), hoàn toàn trái ngược với yêu cầu **Xanh — Trắng** của bản v2.
   - Thư mục `src/Tabs.tsx` mới chỉ là bản nháp với inline styles chắp vá, chưa chia module chuẩn và chưa đáp ứng đầy đủ yêu cầu 6 tab.
   - Thiếu trường **cao độ LiDAR** (`lidar_altitude_m`) trong `Telemetry` interface, backend model và firmware serial JSON.
   - Tab PID Tuning hiện tại là **chỉ đọc (Read-only)**, chưa có chức năng gửi lệnh ghi serial xuống ESP32.
   - Nút "Xin phép bay" chỉ gọi một POST rỗng tới `/api/v1/commands/request_flight`, chưa có modal thu thập thông tin người lái, bằng lái, ngày giờ và GPS.
6. **Hiện trạng MOD Server**:
   - Tệp `backend/mod_server.py` hiện chỉ là một mock script dài 15 dòng trả về token ngẫu nhiên.
   - Cần thiết kế và xây dựng lại thành một dịch vụ độc lập hoàn chỉnh có cơ sở dữ liệu riêng, giao diện quản trị 2 tab, thuật toán cấp vùng bay 1km và cơ chế kiểm soát thời gian bay fail-safe.

---

## 2. KHẢO SÁT & KẾ HOẠCH NÂNG CẤP FRONTEND 6 TABS

### 2.1 Cấu trúc mã nguồn hiện tại (`frontend/src`)

```
frontend/
├── package.json          # React 19.1.1, Three.js 0.179.1, MapLibre GL 5.7.1, Recharts 3.1.2
├── vite.config.ts        # Proxy /api -> http://127.0.0.1:8000, /ws -> ws://127.0.0.1:8000
├── index.html            # Entry HTML, load IBM Plex Mono, Manrope fonts
└── src/
    ├── main.tsx          # Mounts React DOM
    ├── App.tsx           # Điều hướng Login, UserView (Camera), AdminView, SetupAccount
    ├── DashboardPanels.tsx # CameraPanel, DroneModel (3D), PidPanel (Read-only), SerialPanel, PreflightPanel
    ├── FlightMap.tsx     # MapLibre GL + PMTiles offline map (style Dark)
    ├── SetupAccount.tsx  # Modal đổi mật khẩu / email bắt buộc lần đầu
    ├── Tabs.tsx          # Thử nghiệm sơ khai 6 tab với inline style
    ├── api.ts            # Client API wrappers (fetch)
    ├── types.ts          # Interfaces: UserSession, Telemetry, SystemStatus, MapConfig
    └── styles.css        # CSS toàn cục tông đen - xanh ngọc (Cyberpunk Dark)
```

### 2.2 So sánh cấu trúc Tab hiện tại vs 6 Tab yêu cầu

| # | Tab Yêu Cầu v2 | Hiện Trạng Codebase | Đánh Giá & Thiếu Sót |
|---|---|---|---|
| 1 | **Camera** (USB Camera Stream) | `CameraPanel` trong `DashboardPanels.tsx` | Đã có WebRTC/MJPEG iframe; đang dùng style tối màu có hiệu ứng scanline. Cần làm sạch, hiển thị FPS/độ phân giải, nút reload luồng. |
| 2 | **Telemetry & 3D Model** (Roll/Pitch/Yaw + LiDAR Altitude) | `DroneModel` & `AttitudePanel` | Mô hình 3D Three.js chỉ hiển thị Roll, Pitch, Yaw. **HOÀN TOÀN THIẾU độ cao LiDAR**. Cần bổ sung card đo cao độ LiDAR, đổi màu nền 3D sang xám sáng/xanh. |
| 3 | **PID Tuning** (Đọc/Ghi serial) | `PidPanel` trong `DashboardPanels.tsx` | Đang mang nhãn `CHỈ THEO DÕI` (Read-only). **Không có ô nhập Kp, Ki, Kd**, không có nút đọc/ghi xuống ESP32. Cần viết lại thành form tương tác 2 chiều. |
| 4 | **Phiên Đăng Nhập** (Current Session) | `SessionTab` sơ khai trong `Tabs.tsx` | Chỉ là danh sách `<ul>` thô sơ. Cần hiển thị chi tiết tài khoản hiện tại (Họ tên, email, vai trò, thời gian đăng nhập, hạn token, CSRF token) và danh sách session kèm nút thu hồi (Revoke). |
| 5 | **Map** (Drone GPS, Vùng bay mở 1km, Vùng cấm) | `FlightMap.tsx` | Đang dùng basemap Protomaps Dark. Chỉ vẽ vùng cấm/hạn chế cố định. **Chưa vẽ vùng bay 1km được duyệt**, chưa có đồng hồ đếm ngược giờ bay, chưa có badge trạng thái phê duyệt MOD. |
| 6 | **Quản Lý Firmware** (Update/Flash, Xóa FW) | `FirmwareTab` sơ khai trong `Tabs.tsx` | Input file thô sơ, chưa có thông tin phiên bản FW hiện tại, mã băm SHA256, thanh tiến trình nạp, và cơ chế kiểm soát gatekeeper khóa tính năng trước khi nạp FW. |

### 2.3 Chi tiết thiết kế từng Tab & Khoảng trống kỹ thuật (Gaps)

#### Tab 1: Camera (Giám sát hình ảnh trực tiếp)
- **Yêu cầu**: Hiển thị video trực tiếp từ camera USB cắm vào Pi5 qua WebRTC hoặc MJPEG fallback (`/api/v1/camera/stream`).
- **Phân quyền**: Đây là **tab duy nhất** mà tài khoản vai trò `User` (và Admin chưa được duyệt) được phép nhìn thấy.
- **Tính năng cần bổ sung**:
  - Tỉ lệ khung hình cố định (16:9), tự động scale theo màn hình.
  - Overlay thông số: Trạng thái LIVE, độ phân giải phát hiện, độ trễ ước tính (< 1s).
  - Nút bấm làm mới luồng (Reconnect Camera) khi mất tín hiệu.

#### Tab 2: Telemetry & Mô hình 3D (Attitude & LiDAR)
- **Yêu cầu**: Hiển thị mô hình 3D của drone chuyển động theo thời gian thực (5Hz) qua WebSocket `/ws/telemetry`. **Chỉ hiển thị 3 trục Roll / Pitch / Yaw và cao độ đo từ cảm biến LiDAR**.
- **Khoảng trống kỹ thuật phát hiện**:
  1. Trong `frontend/src/types.ts`: `Telemetry` interface chưa có trường `lidar_altitude_m: number | null`.
  2. Trong `backend/app/models.py`: `TelemetryFrame` chưa định nghĩa `lidar_altitude_m: float | None = None`.
  3. Trong `backend/app/serial_io.py`: Hàm `update_esp_line()` chưa parse trường `lidar` từ chuỗi JSONL của ESP32.
  4. Trong `FC_can_bang/display.ino`: Đã có biến `float Altitude_kalman = 0;` nhưng chưa đưa vào đối tượng JSON telemetry gửi lên serial.
- **Giải pháp thiết kế**:
  - Bổ sung trường `lidar: Altitude_kalman` vào chuỗi JSON telemetry trong ESP32.
  - Backend parse và broadcast qua WebSocket.
  - Frontend hiển thị mô hình 3D trên nền Canvas màu xanh nhạt/trắng sáng, bên dưới gồm 4 đồng hồ hiển thị: `ROLL (°)`, `PITCH (°)`, `YAW (°)`, và `ĐỘ CAO LIDAR (m)` dạng Digital Gauge nổi bật.

#### Tab 3: PID Tuning (Đọc & Ghi thông số qua Serial)
- **Yêu cầu**: Cho phép kỹ thuật viên đọc thông số PID hiện tại từ ESP32, chỉnh sửa Kp, Ki, Kd cho từng trục (Roll, Pitch, Yaw), và ghi xuống ESP32 qua kết nối Serial an toàn.
- **Khoảng trống kỹ thuật phát hiện**:
  - Hiện tại `PidPanel` chỉ vẽ Recharts biểu đồ output và bảng tĩnh. Không có endpoint ghi PID xuống serial.
- **Giải pháp thiết kế**:
  - Bổ sung endpoint backend:
    - `GET /api/v1/pid`: Đọc thông số PID hiện tại từ cache/ESP32.
    - `POST /api/v1/pid`: Nhận payload `{ axis: "roll"|"pitch"|"yaw", kp: float, ki: float, kd: float }`, kiểm tra khoảng giá trị hợp lệ (0.0 đến 10.0), gửi lệnh JSONL `{"type":"pid_set", ...}` xuống serial ESP32 và chờ ACK.
  - Giao diện frontend:
    - Bảng nhập dữ liệu trực quan: 3 hàng (Roll, Pitch, Yaw) x 3 cột (Kp, Ki, Kd) dạng input numeric có bước tăng 0.01.
    - 2 nút chức năng chính: `Đọc từ Drone` (Tải lại thông số) và `Ghi xuống Drone` (Lưu & Áp dụng).
    - Biểu đồ thời gian thực Recharts hiển thị sai lệch giữa Setpoint, Measured và Output để người điều khiển quan sát đáp ứng của hệ thống.

#### Tab 4: Tài khoản đang đăng nhập (Session Management)
- **Yêu cầu**: Hiển thị thông tin định danh của người dùng hiện tại và quản lý các phiên làm việc đang hoạt động.
- **Giải pháp thiết kế**:
  - Thẻ thông tin người dùng (Profile Card): Tên tài khoản, Họ và tên, Email, Vai trò (`ADMIN`), Trạng thái 2FA (`Đã bật TOTP`), Thời gian đăng nhập.
  - Bảng danh sách phiên truy cập (`sessions`): Địa chỉ IP, Trình duyệt/Thiết bị, Thời điểm tạo, Thời điểm hết hạn.
  - Nút `Đăng xuất tất cả phiên khác` (gọi `DELETE /api/v1/sessions/other`) để tăng cường an toàn khi vận hành trạm mặt đất.

#### Tab 5: Map (Bản đồ bay & Vùng bay 1km)
- **Yêu cầu**: Bản đồ giám sát vị trí drone theo GPS, hiển thị các vùng cấm bay/hạn chế bay cố định, và **vẽ vùng bay được cấp phép (bán kính 1km)** xung quanh tọa độ đã được MOD duyệt.
- **Khoảng trống kỹ thuật phát hiện**:
  - `FlightMap.tsx` đang nạp style Protomaps Dark. Chưa có logic đọc vùng bay được cấp phép từ MOD Server.
- **Giải pháp thiết kế**:
  - Đổi basemap sang Protomaps Light (`namedFlavor('light')`) hoặc vector style màu xanh trắng hiện đại.
  - Bổ sung GeoJSON Layer động `authorized-flight-zone`:
    - Khi có phê duyệt từ MOD: Vẽ một vòng tròn bán kính 1000m (Polygon 64 đỉnh) màu xanh dương/xanh lục trong suốt (`fill-color: #0284c7`, `fill-opacity: 0.2`, viền đứt đoạn `line-color: #0369a1`).
    - Hiển thị bảng thông tin nổi (Flight Window Widget): Trạng thái `ĐÃ ĐƯỢC CẤP PHÉP`, Giờ bắt đầu - Giờ kết thúc, Thời gian còn lại (đếm ngược theo từng giây).
    - Marker vị trí Drone: Icon drone xoay theo góc `course_deg` của GPS.

#### Tab 6: Quản lý Firmware ESP32
- **Yêu cầu**: Quản lý vòng đời firmware: nạp bản build mới (flash file `.bin`), xóa firmware cũ, và làm chốt chặn an toàn (bắt buộc nạp FW trước khi cho phép điều khiển).
- **Giải pháp thiết kế**:
  - Khung thông tin firmware hiện tại: Trạng thái (`Đã nạp / Sẵn sàng` hoặc `Chưa nạp firmware - Hệ thống bị khóa`), Ngày nạp gần nhất, Mã băm SHA-256 của file binary.
  - Khu vực Upload Firmware: Hỗ trợ chọn file `.bin` hoặc kéo thả, kiểm tra dung lượng hợp lệ (tối đa 4MB).
  - Nút `Nạp Firmware`: Gọi `POST /api/v1/firmware/flash`, hiển thị thanh tiến trình (Erasing -> Flashing -> Verifying -> Hoàn tất), tự động bắt lệnh serial để tái lập kết nối.
  - Nút `Xóa Firmware hiện tại`: Kèm hộp thoại xác nhận cảnh báo an toàn.

---

### 2.4 Modal & Nút "Xin phép bay" trên Header

Căn cứ Mục 5 của đặc tả:
- **Vị trí**: Đặt tại góc trên bên phải của Header thanh tiêu đề Pi5, ngay cạnh thông tin tài khoản admin.
- **Điều kiện hiển thị**: **Chỉ hiển thị với tài khoản Admin đã được duyệt** (`session.role === 'admin' && !session.require_setup`). Tài khoản `User` tuyệt đối không nhìn thấy nút này.
- **Giao diện Modal "Xin phép bay (Flight Permission Request)"**:
  Khi nhấn nút, một hộp thoại Modal hiện đại mở ra gồm các trường thông tin bắt buộc:
  1. **Họ và tên người điều khiển** (`full_name`): Input text, bắt buộc.
  2. **Mã bằng lái bay** (`pilot_license_id`): Input text định dạng mã số giấy phép.
  3. **Ngày bay** (`flight_date`): Input date (`YYYY-MM-DD`), mặc định là ngày hiện tại.
  4. **Khung giờ bay**:
     - *Từ giờ* (`time_from`): Input time (`HH:MM`).
     - *Đến giờ* (`time_to`): Input time (`HH:MM`).
  5. **Tọa độ GPS hiện tại của Drone**:
     - Tự động điền vĩ độ (`latitude`) và kinh độ (`longitude`) lấy từ telemetry GPS hiện tại.
     - Hiển thị trạng thái GPS Fix (Hợp lệ / Vệ tinh SVs / HDOP). Nếu chưa có GPS fix thật trong môi trường giả lập, cho phép chọn tọa độ kiểm thử.
  6. **Bán kính đề xuất**: Cố định là `1000m` (1km) theo đặc tả.
- **Luồng xử lý khi nhấn "Gửi yêu cầu"**:
  - Gửi request `POST /api/v1/commands/request_flight` về backend Pi5.
  - Backend Pi5 đóng gói thông tin, ký xác thực và chuyển tiếp lên MOD Server (`POST /api/v1/mod/flight-requests`).
  - Modal hiển thị trạng thái chuyển tiếp: `Đang gửi yêu cầu...` -> `Đã gửi thành công, đang chờ MOD phê duyệt (Mã yêu cầu: REQ-xxxx)`.

---

### 2.5 Phân quyền giao diện theo Role & Gatekeeper lần đầu

Hệ thống phân quyền UI tuân thủ nghiêm ngặt 3 cấp độ:

```
[Truy cập Web Pi5]
       │
       ▼
 [Chưa đăng nhập] ──────────► [Trang Login / Đăng ký] (Màu xanh - trắng)
       │
       ▼
[Đã xác thực danh tính]
       │
       ├──► [Lần đầu Admin mặc định] ──► BẮT BUỘC: [Trang đổi Email + OTP xác nhận] (Chặn mọi tab)
       │
       ├──► [Vai trò USER] ──────────► CHỈ XEM: [Tab 1: Camera] (Ẩn 5 tab còn lại, ẩn nút Xin bay)
       │
       ├──► [Admin chờ duyệt] ───────► CHỈ XEM: [Tab 1: Camera] + Banner "Đang chờ Admin duyệt quyền"
       │
       └──► [Admin đã duyệt]
                  │
                  ├──► [Chưa nạp Firmware] ──► BẮT BUỘC: [Tab 6: Nạp Firmware] (Khóa các tab 2,3,5)
                  │
                  └──► [Đã nạp Firmware]  ──► MỞ ĐỦ 6 TAB + Nút "Xin phép bay" trên Header
```

---

## 3. ĐẶC TẢ HỆ THỐNG THIẾT KẾ THEME XANH — TRẮNG (BLUE-WHITE)

### 3.1 Đánh giá phong cách giao diện hiện tại
- **File CSS hiện tại** (`frontend/src/styles.css`): Khai báo `:root { --bg:#04090c; --panel:#081216; --line:#19343c; --teal:#35e6c1; }`.
- **Nhận định**: Phong cách tối màu mang tính chất phòng lab, độ tương phản chói lóa ngoài trời kém, không đồng bộ với giao diện Captive Portal của ESP32 và vi phạm yêu cầu số 1 và số 9 của đặc tả v2: *"Đổi giao diện sang tông xanh — trắng, nhất quán trên mọi trang"*.

### 3.2 Bảng mã màu & Design Tokens (Blue-White Aviation GCS)

Để tạo nên giao diện trạm mặt đất chuyên nghiệp, rõ ràng dưới ánh sáng ban ngày, chúng tôi đề xuất hệ thống Design Tokens sau:

```css
:root {
  /* Font typography */
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'IBM Plex Mono', 'JetBrains Mono', monospace;

  /* Primary Blue Palette */
  --color-primary-50: #eff6ff;
  --color-primary-100: #dbeafe;
  --color-primary-200: #bfdbfe;
  --color-primary-500: #3b82f6;
  --color-primary-600: #2563eb;  /* Màu chủ đạo nút bấm, highlight */
  --color-primary-700: #1d4ed8;  /* Màu nhấn tiêu đề, brand */
  --color-primary-900: #1e3a8a;

  /* Sky & Cyan Accents */
  --color-sky-500: #0ea5e9;
  --color-sky-100: #e0f2fe;

  /* Neutral Slate / White Palette */
  --bg-app: #f8fafc;           /* Nền tổng thể toàn trang (Slate 50) */
  --bg-surface: #ffffff;       /* Nền các Card, Panel, Modal (Trắng thuần) */
  --bg-surface-subtle: #f1f5f9;/* Nền bảng, ô input (Slate 100) */
  
  /* Borders & Dividers */
  --border-light: #e2e8f0;     /* Viền nhẹ Slate 200 */
  --border-focus: #3b82f6;     /* Viền khi focus input */

  /* Text Colors */
  --text-main: #0f172a;        /* Chữ chính (Slate 900) độ tương phản cao */
  --text-secondary: #475569;   /* Chữ phụ (Slate 600) */
  --text-muted: #94a3b8;       /* Chữ mờ / placeholder (Slate 400) */

  /* Semantic Status Colors */
  --status-safe-bg: #ecfdf5;
  --status-safe-text: #065f46;
  --status-safe-border: #10b981;  /* Xanh lục an toàn / GPS Live */

  --status-warn-bg: #fffbeb;
  --status-warn-text: #92400e;
  --status-warn-border: #f59e0b;  /* Vàng cảnh báo */

  --status-danger-bg: #fef2f2;
  --status-danger-text: #991b1b;
  --status-danger-border: #ef4444;/* Đỏ vi phạm vùng cấm / Lỗi ARM */

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.07), 0 2px 4px -2px rgb(0 0 0 / 0.05);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.08), 0 4px 6px -4px rgb(0 0 0 / 0.04);
}
```

### 3.3 Quy chuẩn giao diện Captive Portal ESP32 & Web Pi5

1. **Captive Portal ESP32 (`FC_can_bang/FC_can_bang.ino`)**:
   - Hiện tại mã nguồn đã có: `background-color: #f0f4f8; h2 { color: #0056b3; } .card { background: white; }`.
   - Cần tinh chỉnh nhẹ CSS nhúng trong string C++ để sử dụng màu `--color-primary-600: #2563eb`, bo góc 12px, nút bấm bo góc 8px phẳng, tạo sự chuyển tiếp thị giác mượt mà khi người dùng chuyển từ Captive Portal sang Web Pi5.
2. **Web chính trên Pi5 (`frontend/src/styles.css`)**:
   - Thay thế toàn bộ theme đen cyberpunk bằng theme xanh-trắng dựa trên bảng tokens trên.
   - Header: Nền trắng `#ffffff`, viền đáy `1px solid #e2e8f0`, logo Drone Station màu xanh `linear-gradient(135deg, #2563eb, #0ea5e9)`.
   - Các Panel: Nền trắng bo góc 12px, viền mỏng `#e2e8f0`, đổ bóng nhẹ `--shadow-sm`.
   - Map: Protomaps basemap light, các vùng cấm giữ màu đỏ bán trong suốt, vùng bay được cấp phép hiển thị màu xanh dương trong suốt.
   - Mô hình 3D: Nền Canvas chuyển sắc từ xám nhạt `#f8fafc` sang trắng `#ffffff`, màu drone sơn xám kim loại và xanh cobalt.

---

## 4. THIẾT KẾ TOÀN DIỆN MÁY CHỦ BỘ QUỐC PHÒNG (MOD SERVER)

### 4.1 Kiến trúc hệ thống & Ngăn xếp công nghệ
Căn cứ Mục 7 của đặc tả:
- **Đặc tính vận hành**: Máy chủ độc lập (chạy trên PC riêng hoặc Cloud VPS), không phụ thuộc mạng LAN của Pi5, mở cổng ra Internet (WAN) để có thể truy cập từ bất kỳ đâu.
- **Ngăn xếp công nghệ đề xuất**:
  - **Backend**: Python FastAPI + Uvicorn (cổng mặc định `9000` hoặc `8443` HTTPS). Sử dụng chung chuẩn thư viện với dự án để tái sử dụng mã nguồn và kiểm thử dễ dàng.
  - **Cơ sở dữ liệu**: SQLite3 với chế độ WAL (`PRAGMA journal_mode=WAL;`), lưu tại `mod_data/mod_server.db`. Chế độ WAL đảm bảo đọc ghi đồng thời tốc độ cao, không cần cài đặt DBMS phức tạp.
  - **Frontend MOD UI**: Giao diện Single Page Application hiện đại (HTML5 + Tailwind CSS + MapLibre GL) được FastAPI phục vụ trực tiếp tại root `/` hoặc `/admin`.
  - **Tiến trình nền (Background Scheduler)**: Sử dụng `asyncio` task định kỳ kiểm tra hạn bay mỗi 10 giây để tự động chuyển trạng thái vùng bay từ `APPROVED` sang `EXPIRED`.

### 4.2 Thiết kế cơ sở dữ liệu (Schema & Entities)

```sql
-- Bảng tài khoản MOD Server
CREATE TABLE IF NOT EXISTS mod_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    organization TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'officer')),
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED')),
    created_at TEXT NOT NULL,
    approved_at TEXT,
    approved_by TEXT
);

-- Bảng yêu cầu cấp phép bay
CREATE TABLE IF NOT EXISTS mod_flight_requests (
    id TEXT PRIMARY KEY, -- UUID
    drone_id TEXT NOT NULL,
    pilot_name TEXT NOT NULL,
    license_id TEXT NOT NULL,
    flight_date TEXT NOT NULL,       -- YYYY-MM-DD
    time_from TEXT NOT NULL,         -- HH:MM
    time_to TEXT NOT NULL,           -- HH:MM
    latitude REAL NOT NULL,          -- Tọa độ trung tâm tâm vùng bay
    longitude REAL NOT NULL,
    radius_m REAL NOT NULL DEFAULT 1000.0, -- Bán kính 1km
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', 'REVOKED')),
    permission_token TEXT UNIQUE,    -- MOD-YYYYMMDD-XXXX
    polygon_geojson TEXT,            -- GeoJSON polygon 64 đỉnh của vùng bay 1km
    requested_at TEXT NOT NULL,
    reviewed_at TEXT,
    reviewed_by TEXT,
    rejection_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_mod_req_drone ON mod_flight_requests(drone_id);
CREATE INDEX IF NOT EXISTS idx_mod_req_status ON mod_flight_requests(status);

-- Bảng danh mục vùng cấm bay / hạn chế bay (No-Fly Zones)
CREATE TABLE IF NOT EXISTS mod_geofence_zones (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    zone_type TEXT NOT NULL CHECK(zone_type IN ('prohibited', 'restricted')),
    geometry_geojson TEXT NOT NULL,  -- GeoJSON Polygon hoặc MultiPolygon
    min_altitude_m REAL DEFAULT 0,
    max_altitude_m REAL DEFAULT 500,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Nhật ký kiểm toán bảo mật MOD
CREATE TABLE IF NOT EXISTS mod_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    actor_username TEXT NOT NULL,
    action TEXT NOT NULL,            -- 'APPROVE_FLIGHT', 'REJECT_FLIGHT', 'CREATE_ZONE', 'DELETE_ZONE', etc.
    target_id TEXT,
    details TEXT,
    ip_address TEXT
);
```

### 4.3 Đặc tả API Contracts

#### A. Nhóm API giao tiếp giữa Pi5 và MOD Server:
1. `POST /api/v1/mod/flight-requests`: Pi5 gửi yêu cầu xin bay.
   - **Payload**:
     ```json
     {
       "drone_id": "DRONE-PI5-001",
       "pilot_name": "Nguyen Van A",
       "license_id": "VN-UAV-2026-8899",
       "flight_date": "2026-09-13",
       "time_from": "14:00",
       "time_to": "16:00",
       "latitude": 10.762622,
       "longitude": 106.660172,
       "timestamp": 1789378800,
       "nonce": "a7c8e9b14f",
       "signature": "hmac_sha256_signature_hex"
     }
     ```
   - **Response (201 Created)**:
     ```json
     {
       "request_id": "b3e944fc-1122-44aa-88bb-123456789abc",
       "status": "PENDING",
       "message": "Yêu cầu đã được tiếp nhận, đang chờ phê duyệt"
     }
     ```

2. `GET /api/v1/mod/drone/{drone_id}/permission`: Pi5 kiểm tra giấy phép bay còn hiệu lực.
   - **Response khi ĐÃ DUYỆT (200 OK)**:
     ```json
     {
       "status": "APPROVED",
       "permission_token": "MOD-20260913-9821",
       "drone_id": "DRONE-PI5-001",
       "center": { "latitude": 10.762622, "longitude": 106.660172 },
       "radius_m": 1000.0,
       "valid_from": "2026-09-13T14:00:00Z",
       "valid_to": "2026-09-13T16:00:00Z",
       "time_remaining_s": 5420,
       "polygon_geojson": { "type": "Polygon", "coordinates": [...] }
     }
     ```
   - **Response khi CHƯA DUYỆT hoặc ĐÃ HẾT HẠN (200 OK)**:
     ```json
     {
       "status": "EXPIRED", // hoặc "PENDING" / "REJECTED" / "NO_RECORD"
       "permission_token": null,
       "armed_allowed": false,
       "message": "Không có vùng bay hợp lệ. Lệnh ARM bị khóa."
     }
     ```

3. `GET /api/v1/mod/geofence/zones`: Pi5 tải danh sách toàn bộ vùng cấm/hạn chế bay mới nhất từ MOD.

#### B. Nhóm API cho giao diện quản trị MOD UI:
- `POST /api/v1/mod/auth/register`: Đăng ký tài khoản MOD mới (mặc định trạng thái `PENDING`).
- `POST /api/v1/mod/auth/login`: Đăng nhập lấy JWT cookie.
- `GET /api/v1/mod/admin/requests`: Lấy danh sách yêu cầu bay (hỗ trợ lọc `PENDING`, `APPROVED`, `EXPIRED`).
- `POST /api/v1/mod/admin/requests/{id}/approve`: Duyệt yêu cầu bay (tạo polygon 1km và cấp token).
- `POST /api/v1/mod/admin/requests/{id}/reject`: Từ chối yêu cầu (kèm lý do).
- `POST /api/v1/mod/admin/users/{id}/approve`: Admin MOD duyệt tài khoản đăng ký mới.
- `POST /api/v1/mod/admin/zones`: Tạo vùng cấm bay mới vẽ trên bản đồ.
- `DELETE /api/v1/mod/admin/zones/{id}`: Xóa vùng cấm bay.

### 4.4 Thuật toán Geofencing động (Bán kính 1km & Tự động hết hạn)

#### A. Thuật toán tạo Polygon hình tròn 1000m Geodesic:
Để tạo vùng bay 1km chính xác trên bề mặt Trái Đất (WGS84), máy chủ tính toán 64 điểm tọa độ tạo thành đa giác khép kín:
```python
def generate_geodesic_circle(lat: float, lon: float, radius_m: float = 1000.0, num_points: int = 64) -> dict:
    coords = []
    r_earth = 6378137.0 # Bán kính Trái Đất theo WGS84
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    d_div_r = radius_m / r_earth

    for i in range(num_points + 1):
        bearing = 2 * math.pi * i / num_points
        pt_lat = math.asin(math.sin(lat_rad) * math.cos(d_div_r) +
                           math.cos(lat_rad) * math.sin(d_div_r) * math.cos(bearing))
        pt_lon = lon_rad + math.atan2(math.sin(bearing) * math.sin(d_div_r) * math.cos(lat_rad),
                                      math.cos(d_div_r) - math.sin(lat_rad) * math.sin(pt_lat))
        coords.append([round(math.degrees(pt_lon), 6), round(math.degrees(pt_lat), 6)])
        
    return {
        "type": "Polygon",
        "coordinates": [coords]
    }
```

#### B. Cơ chế tự động đóng vùng bay khi hết giờ:
1. Mỗi yêu cầu duyệt bay gắn liền với mốc thời gian `valid_from` và `valid_to` (UTC).
2. Background Worker trên MOD Server chạy lặp mỗi 10 giây:
   ```python
   UPDATE mod_flight_requests 
   SET status = 'EXPIRED' 
   WHERE status = 'APPROVED' AND datetime('now') > datetime(valid_to);
   ```
3. Khi Pi5 gửi heartbeat hoặc đánh giá lệnh ARM:
   - Nếu thời gian hiện tại `now > valid_to`: Trạng thái lập tức chuyển sang `EXPIRED`.
   - Vùng bay 1km bị thu hồi.
   - Động cơ an toàn Pi5 lập tức kích hoạt lệnh khóa ARM (`status_arm = 0` và gửi cảnh báo cấm cất cánh).

### 4.5 Cơ chế chống tấn công phát lại (Anti-Replay) & Bảo mật kết nối
Do MOD Server mở ra ngoài WAN/Internet, nguy cơ kẻ xấu bắt gói tin xin bay cũ rồi gửi lại (Replay Attack) là rất lớn. Các giải pháp bảo mật bắt buộc:
1. **Kiểm tra độ lệch thời gian (Timestamp Window)**: Mỗi request gửi lên phải có trường `timestamp`. MOD Server từ chối mọi gói tin có độ lệch thời gian lớn hơn ±300 giây (5 phút) so với đồng hồ máy chủ.
2. **Bộ nhớ đệm Nonce (Nonce Cache)**: Mỗi request mang một chuỗi ngẫu nhiên duy nhất `nonce` (16 bytes hex). MOD lưu các `nonce` trong bảng `recent_nonces` với TTL 10 phút. Nếu một `nonce` xuất hiện lần thứ hai trong khung thời gian hợp lệ, request bị từ chối ngay lập tức với mã lỗi `403 Forbidden`.
3. **Chữ ký số HMAC-SHA256**: Payload được ký bằng khóa bí mật giữa Pi5 và MOD Server (`DRONE_SECRET_KEY`). Kẻ tấn công trên đường truyền không thể sửa đổi tọa độ GPS hay thời gian xin bay mà không làm hỏng chữ ký.
4. **Rate Limiting**: Giới hạn tối đa 5 request/phút đối với endpoint đăng ký và 30 request/phút đối với endpoint kiểm tra trạng thái bay.

---

## 5. CHI TIẾT 16 KỊCH BẢN KIỂM THỬ SSH TỰ ĐỘNG (BẢNG 12.1)

### 5.1 Bảng chi tiết 16 kịch bản kiểm thử

Căn cứ Mục 12 và Bảng 12.1 của đặc tả, dưới đây là phân tích chi tiết từng kịch bản kiểm thử:

| # | Tên Tính Năng | Mục Tiêu Kiểm Thử | Phương Pháp Thực Hiện (SSH / Automation) | Kết Quả Kỳ Vọng (Pass Criteria) |
|---|---|---|---|---|
| **1** | **ESP32 AP + Captive Portal** | Xác nhận ESP32 phát AP khi chưa cấu hình Wi-Fi và mở portal chọn mạng. | Gửi lệnh reset config qua serial (`{"type":"wifi_reset"}`), kiểm tra ESP32 phát SSID `Drone-Setup-AP`, kết nối HTTP GET `/` vào portal. | Portal trả về HTML giao diện xanh-trắng chứa danh sách Wi-Fi dò được; POST `/connect` nhận `200 OK`. |
| **2** | **Pi5 lên mạng sau provisioning** | Xác nhận Pi5 nhận thông tin Wi-Fi, kết nối thành công và phản hồi trạng thái cho ESP32. | Theo dõi `journalctl -u iot-drone` sau khi gửi gói tin `wifi_setup` qua serial. Kiểm tra endpoint `/status` trên ESP32. | ESP32 hiển thị đúng IP của Pi5 (vd `192.168.1.118`), URL web `https://...`, ID drone và tài khoản mặc định. |
| **3** | **Giao tiếp serial Pi5 ⇄ ESP32** | Kiểm tra độ ổn định và tính toàn vẹn của giao thức JSONL qua cổng USB serial. | Gửi lệnh kiểm thử qua serial (hoặc cổng PTY giả lập), đo thời gian và định dạng gói tin ACK phản hồi. | Nhận gói tin ACK `{"type":"ack","command_id":...,"accepted":true}` đúng định dạng JSON, thời gian phản hồi < 100ms, không rơi rụng ký tự. |
| **4** | **Đăng ký + OTP + 2FA** | Xác minh luồng đăng ký người dùng mới với xác thực email OTP và TOTP 2FA. | Script tự động gọi API `POST /api/v1/auth/register`, trích xuất OTP từ log/mock email, xác thực OTP, gửi mã TOTP PyOTP. | User kích hoạt ngay, chỉ xem Camera. Admin chuyển sang trạng thái chờ duyệt (quyền như User cho đến khi được duyệt). |
| **5** | **Admin mặc định ép đổi email + OTP** | Đảm bảo tài khoản admin mặc định (`pi5`) không thể làm gì khác trước khi hoàn thành cập nhật email & OTP. | Đăng nhập tài khoản mặc định `pi5`/`123456`, thử gọi các API quản trị (`/api/v1/status`, `/api/v1/commands/*`). | Hệ thống trả về `403 Forbidden` kèm cờ `require_setup: true`. Thao tác chỉ mở lại sau khi xác nhận mã OTP email thành công. |
| **6** | **Bắt buộc nạp FW trước khi dùng** | Xác nhận chốt chặn an toàn: không cho phép thao tác điều khiển khi chưa nạp firmware cho ESP32. | Đăng nhập tài khoản admin đã duyệt, xóa cờ firmware (`FIRMWARE_FLAG_FILE`), thử gọi lệnh ARM hoặc đổi PID. | Hệ thống chặn thao tác, trả về mã lỗi `FIRMWARE_NOT_FLASHED`, giao diện chỉ cho phép truy cập Tab Quản lý FW. |
| **7** | **Camera Stream** | Kiểm tra tính sẵn sàng và độ ổn định của luồng video từ USB camera cắm trên Pi5. | Gọi endpoint `/api/v1/camera/status`, kéo khung hình từ stream WebRTC/MJPEG qua HTTP GET trong 10 giây. | `available == true`, luồng video liên tục, không bị treo hoặc rớt khung hình, HTTP stream trả về `multipart/x-mixed-replace`. |
| **8** | **Telemetry 3D (Attitude + LiDAR)** | Xác thực luồng telemetry 5Hz truyền đúng 3 trục Roll/Pitch/Yaw và cao độ đo từ cảm biến LiDAR. | Mở kết nối WebSocket `/ws/telemetry` từ test script, đọc liên tục 30 frames, so sánh với dữ liệu cảm biến mô phỏng. | Khung tin nhận đều đặn ~5Hz, chứa đầy đủ `attitude.roll`, `pitch`, `yaw` và `lidar_altitude_m`, sai lệch số liệu = 0. |
| **9** | **PID Tuning (Đọc/Ghi serial)** | Kiểm tra khả năng gửi thông số PID mới xuống ESP32 và đọc lại xác nhận qua cổng serial. | Gửi `POST /api/v1/pid` với giá trị Kp=1.2, Ki=0.3, Kd=0.08. Đọc gói tin xác nhận từ serial và truy vấn lại `GET /api/v1/pid`. | ESP32 lưu giá trị mới, phản hồi ACK thành công, không gây ngắt kết nối hay treo cổng serial. |
| **10** | **Xin phép bay → MOD Server** | Kiểm tra nút "Xin phép bay" thu thập đủ trường dữ liệu và gửi thành công lên MOD Server. | Script gọi `POST /api/v1/commands/request_flight` kèm họ tên, mã bằng lái, khung giờ và tọa độ GPS hiện tại. | MOD Server nhận được request, lưu vào bảng `mod_flight_requests` với đủ tọa độ GPS và thông tin người lái. |
| **11** | **Duyệt bay → Mở vùng bay 1km** | Xác nhận sau khi admin MOD phê duyệt, Pi5 nhận được trạng thái và mở vùng bay 1km tương ứng. | Gọi API MOD `POST /api/v1/mod/admin/requests/{id}/approve`. Chờ Pi5 cập nhật trạng thái qua polling/webhook. | Pi5 chuyển trạng thái "ĐÃ ĐƯỢC DUYỆT", mở vùng bay bán kính 1km quanh tọa độ GPS, cờ an toàn cho phép ARM chuyển sang `true`. |
| **12** | **Hết giờ bay → Tự đóng vùng bay** | Kiểm tra cơ chế fail-safe tự động hết hạn vùng bay và khóa lệnh ARM khi quá khung giờ cho phép. | Chỉnh đồng hồ bay giả lập vượt quá `time_to` đã duyệt. Đợi background worker MOD kích hoạt hết hạn. | Trạng thái vùng bay chuyển thành `EXPIRED`, vùng bay 1km bị xóa khỏi động cơ geofence, lệnh ARM lập tức bị khóa trở lại. |
| **13** | **Khóa ARM khi chưa duyệt / ngoài vùng** | Kiểm tra nghiêm ngặt quy tắc an toàn: từ chối ARM nếu không có giấy phép hoặc drone nằm ngoài vùng bay 1km. | 1) Thử gửi lệnh ARM khi chưa xin phép bay.<br>2) Xin phép tại điểm A, bơm tọa độ GPS tại điểm B (cách A 1.5km) rồi thử ARM. | ESP32 kiên quyết từ chối ARM (`status_arm = 0`), backend ghi nhật ký kiểm toán vi phạm, cảnh báo hiển thị trên giao diện. |
| **14** | **Quản lý Firmware (Update & Xóa)** | Kiểm tra chức năng nạp firmware mới (upload file `.bin`) và xóa firmware để đưa hệ thống về trạng thái an toàn. | 1) Upload firmware test hợp lệ qua `POST /api/v1/firmware/flash`.<br>2) Gọi `DELETE /api/v1/firmware/delete`. | Upload thành công thiết lập cờ FW hoạt động; Xóa FW xóa cờ và lập tức khóa các chức năng điều khiển bay. |
| **15** | **MOD Server: Đăng ký cần duyệt** | Kiểm tra quy trình phê duyệt tài khoản mới trên MOD Server. | Gửi `POST /api/v1/mod/auth/register` tạo tài khoản `mod_user_test`. Thử đăng nhập ngay. | Đăng nhập bị chặn với thông báo "Tài khoản đang chờ duyệt". Sau khi Admin MOD gọi `/approve`, đăng nhập thành công. |
| **16** | **Vẽ / Xóa vùng cấm bay trên MOD** | Kiểm tra chức năng vẽ đa giác vùng cấm bay, lưu trữ GeoJSON và đồng bộ xuống Pi5. | Gọi `POST /api/v1/mod/admin/zones` với GeoJSON đa giác phức tạp (10 đỉnh). Kiểm tra `geofence.py` load và tính toán. | Động cơ Geofence nạp thành công không bị crash, phát hiện chính xác trạng thái `breach`/`safe` khi drone chạm biên. |

---

### 5.2 Kiến trúc Test Harness tự động qua SSH (Paramiko Runner)

Để kiểm thử 16 kịch bản trên một cách tự động, độc lập và có thể chạy lặp lại trong quy trình CI/CD, chúng tôi thiết kế bộ chạy kiểm thử **`scripts/run_ssh_tests.py`** sử dụng thư viện `paramiko` đã có sẵn trong Python.

#### Sơ đồ khối Test Harness:
```
┌───────────────────────────────────────────────────────────┐
│               TEST RUNNER TRÊN MÁY DEV / CI               │
│               (scripts/run_ssh_tests.py)                  │
└─────────────────────────────┬─────────────────────────────┘
                              │ SSH Connection (Port 22)
                              │ pi5@192.168.1.118
                              ▼
┌───────────────────────────────────────────────────────────┐
│                 RASPBERRY PI 5 (TARGET HOST)              │
│                                                           │
│  1. Quản lý Service: systemctl restart iot-drone          │
│  2. Môi trường Python: /opt/iot-drone/venv/bin/pytest     │
│  3. Thu thập Log: journalctl -u iot-drone -n 200          │
│  4. Hardware-in-loop & Mock Fixtures:                     │
│     - Pseudo-terminal (PTY) giả lập Serial ESP32          │
│     - NMEA GPS Simulator (Baud 38400 / Socket)            │
│     - V4L2loopback / MJPEG Camera Stream                  │
│     - Local MOD Server Instance (Port 9000)               │
└───────────────────────────────────────────────────────────┘
```

### 5.3 Môi trường giả lập Mock Fixtures

Để kiểm thử tự động 100% không phụ thuộc vào việc bật/tắt thiết bị thật:
1. **Mock Serial ESP32 bằng PTY (`os.openpty`)**:
   - Tạo cặp master/slave virtual serial port `/tmp/ttyV0` và `/tmp/ttyV1`.
   - Script giả lập đọc lệnh JSONL từ Pi5 (`{"type":"command",...}`) và tự động phản hồi ACK hoặc đẩy telemetry 5Hz chứa cao độ LiDAR.
2. **Mock GPS NMEA Stream**:
   - Ghi định kỳ các câu chuẩn NMEA `$GPGGA`, `$GPRMC` vào cổng serial giả lập để test định vị hợp lệ, mất tín hiệu GPS (stale), và tọa độ dịch chuyển ra ngoài bán kính 1km.
3. **Mock MOD Server**:
   - Khởi động instance MOD Server thật trên cổng 9000 tại localhost của Pi5 hoặc máy trạm để test trọn vẹn luồng HTTP REST API, kiểm tra chữ ký HMAC và tự động hết hạn sau N giây.

### 5.4 Hiện trạng kết nối Pi5 thực tế & Khắc phục lỗi SyntaxError phát hiện

Trong quá trình khảo sát, chúng tôi đã trực tiếp kết nối SSH và chạy thử nghiệm trên Pi5:
- **Lệnh thực thi**: `ssh pi5@192.168.1.118` (sử dụng mật khẩu `123456`).
- **Thử nghiệm chạy test**: `PYTHONPATH=. /opt/iot-drone/venv/bin/pytest tests/test_core.py` -> **KẾT QUẢ: 7/7 PASSED**.
- **Thử nghiệm chạy test API**: `PYTHONPATH=. /opt/iot-drone/venv/bin/pytest tests/test_api.py` -> **KẾT QUẢ: FAILED (SyntaxError)**.
  - *Nguyên nhân*: Tệp `backend/app/main.py` dòng 68 có ký tự thoát dòng lỗi `\n` và dòng 147 có cú pháp decorator sai.
  - *Phương án khắc phục đề xuất*: Chuẩn hóa lại dòng 67-69 và dòng 147 trong `backend/app/main.py` để test suite khôi phục trạng thái hoạt động bình thường.

---

## 6. LỘ TRÌNH TRIỂN KHAI & ĐỀ XUẤT CHO CÁC NHÓM KỸ THUẬT

### 6.1 Giai đoạn 1: Sửa chữa Blocker & Nâng cấp Giao thức Dữ liệu
1. **Hotfix `backend/app/main.py`**: Sửa lỗi cú pháp dòng 68 và 147 để toàn bộ test suite backend chạy pass 100%.
2. **Mở rộng Telemetry & Serial Protocol**:
   - Bổ sung trường `lidar_altitude_m` vào `TelemetryFrame` trong `models.py`.
   - Cập nhật parser trong `serial_io.py` và `FC_can_bang/display.ino` để truyền nhận số liệu LiDAR.
   - Bổ sung endpoint điều khiển PID (`GET /api/v1/pid`, `POST /api/v1/pid`).

### 6.2 Giai đoạn 2: Tái cấu trúc Frontend & Áp dụng Theme Xanh — Trắng
1. **Thay thế CSS Theme**: Cập nhật `src/styles.css` theo bảng Design Tokens Xanh — Trắng đã thiết kế ở Mục 3.2.
2. **Xây dựng 6 Tab Hoàn Chỉnh**:
   - Tách rời các tab thành component độc lập: `TabCamera`, `TabTelemetry3D`, `TabPidTuning`, `TabSession`, `TabFlightMap`, `TabFirmware`.
   - Thiết kế Modal "Xin phép bay" trên Header với đầy đủ các trường thông tin theo Mục 2.4.
   - Thêm Form Đăng ký tài khoản mới kèm quy trình nhập OTP email và 2FA TOTP.
   - Khóa các tab điều khiển khi chưa nạp firmware (Firmware Gatekeeper).

### 6.3 Giai đoạn 3: Triển khai Độc lập MOD Server
1. **Viết mã nguồn MOD Server hoàn chỉnh**: Tạo thư mục `mod_server/` chứa `app/main.py`, `app/models.py`, `app/db.py`, `app/geofence_engine.py`.
2. **Triển khai UI Quản trị MOD**: Giao diện xanh-trắng 2 tab (Quản lý cấp phép bay & Vẽ vùng cấm bay trên MapLibre).
3. **Tích hợp Dynamic Geofence**: Hoàn thiện thuật toán sinh Polygon tròn 1km và Background Worker kiểm tra hết hạn sau khung giờ bay.

### 6.4 Giai đoạn 4: Tự động hóa Kiểm thử 16 Kịch bản SSH
1. **Viết bộ kiểm thử `tests/ssh_e2e/test_16_scenarios.py`** tích hợp Paramiko Runner.
2. **Chạy nghiệm thu tự động** trên Pi5 `192.168.1.118`, ghi log Pass/Fail chi tiết từng mục theo Bảng 12.1.
3. **Xuất báo cáo nghiệm thu và báo cáo bảo mật** bàn giao cho Orchestrator.

---
*Báo cáo được lập bởi Explorer 3 — Hoàn thành nhiệm vụ khảo sát.*
