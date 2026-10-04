# 🚁 F450 PNT PVD — Hệ thống Quản lý Vùng bay & Điều khiển Drone IoT

> **Dự án nghiên cứu** của Phạm Ngọc Tấn và Phan Văn Đông  
> Mô hình quản lý vùng cấm bay, cấp phép bay và giám sát drone thời gian thực — không phải cổng thông tin chính thức của cơ quan nhà nước.

---

## 📑 Mục lục

- [Tổng quan](#-tổng-quan)
- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Luồng hoạt động](#-luồng-hoạt-động)
- [Tính năng](#-tính-năng)
- [Bảo mật](#-bảo-mật)
- [Cấu trúc mã nguồn](#-cấu-trúc-mã-nguồn)
- [Cài đặt & Triển khai](#-cài-đặt--triển-khai)
- [Biến môi trường](#-biến-môi-trường)
- [Kiểm thử](#-kiểm-thử)
- [API Contracts](#-api-contracts)
- [Phụ lục kỹ thuật](#-phụ-lục-kỹ-thuật)

---

## 🎯 Tổng quan

Hệ thống IoT 3 tầng phục vụ quản lý vùng cấm bay và điều khiển drone F450:

| Tầng | Phần cứng | Vai trò |
|------|-----------|---------|
| **Server PC** | Máy tính cá nhân | Bản đồ vùng bay, duyệt yêu cầu bay, quản lý tài khoản, giám sát telemetry |
| **Pi 5 Gateway** | Raspberry Pi 5 | Cổng trung gian: kết nối ESP32, camera, GPS, gửi đơn bay lên PC |
| **ESP32 Firmware** | ESP32 DevKit | Flight controller: PID cân bằng, SBUS RC, giới hạn độ cao, khóa ARM |

**Nguyên lý cốt lõi:**
- Drone **không thể ARM** nếu chưa có cấp phép bay từ cán bộ trên PC server.
- Pi 5 chỉ cấp/thu hồi **quyền ARM** (`$AUTH,ALLOW` / `$AUTH,DENY`), không bao giờ gửi lệnh ARM/DISARM hay quay motor.
- Mọi giao tiếp Pi ↔ PC được mã hóa bằng phong bì AES-256-GCM.

---

## 🏗 Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNET / LAN                           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    SERVER PC (FastAPI)                     │  │
│  │                                                           │  │
│  │  ┌─────────────┐  ┌──────────┐  ┌──────────────────────┐ │  │
│  │  │  React 19   │  │ REST API │  │     SQLite DB        │ │  │
│  │  │  Frontend   │◄►│ FastAPI  │◄►│  Users, Zones,       │ │  │
│  │  │  (Vite 7)   │  │ :8765    │  │  Flights, Audit,     │ │  │
│  │  │             │  │          │  │  Sessions, Devices   │ │  │
│  │  └─────────────┘  └────┬─────┘  └──────────────────────┘ │  │
│  │                        │                                   │  │
│  │         SSE Telemetry ▼ REST + AES-256-GCM envelopes      │  │
│  └────────────────────────┼───────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────┼───────────────────────────────────┐  │
│  │              RASPBERRY PI 5 (FastAPI + ES Modules UI)      │  │
│  │                        │                                   │  │
│  │  ┌──────────┐  ┌──────┴──────┐  ┌─────────┐  ┌─────────┐│  │
│  │  │ Web UI   │  │ Authority   │  │ Camera  │  │ Network ││  │
│  │  │ :80      │  │ Client      │  │ MJPEG   │  │ nmcli   ││  │
│  │  │ (ES Mod) │  │ (Crypto)    │  │ Stream  │  │ Wi-Fi   ││  │
│  │  └──────────┘  └──────┬──────┘  └─────────┘  └─────────┘│  │
│  │                       │                                   │  │
│  │              UART/USB ▼ $PING/$AUTH/$TELE                 │  │
│  └───────────────────────┼───────────────────────────────────┘  │
│                          │                                       │
│  ┌───────────────────────┼───────────────────────────────────┐  │
│  │                  ESP32 FLIGHT CONTROLLER                   │  │
│  │                       │                                   │  │
│  │  ┌────────┐  ┌───────┴───┐  ┌──────┐  ┌──────┐  ┌─────┐│  │
│  │  │ICM20602│  │Flight Gate│  │ GPS  │  │ Baro │  │SBUS ││  │
│  │  │  IMU   │  │ARM/DISARM │  │ NMEA │  │BMP388│  │ RC  ││  │
│  │  └────┬───┘  └───────────┘  └──────┘  └──────┘  └──┬──┘│  │
│  │       │                                              │   │  │
│  │       ▼           PID Controller                     │   │  │
│  │  ┌─────────────────────────────────────────────────┐ │   │  │
│  │  │  ESC 1 (M1)  ESC 2 (M2)  ESC 3 (M3)  ESC 4 (M4)│◄┘   │  │
│  │  └─────────────────────────────────────────────────┘     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Luồng hoạt động

### 1. Luồng đăng ký & xác thực (PC Server)

```
Người dùng ──► Đăng ký (email + mật khẩu + username)
                  │
                  ▼
              Gửi OTP qua email ──► Xác nhận OTP
                  │
                  ▼
              Thiết lập TOTP 2FA (quét QR code)
                  │
                  ▼
              Chấp nhận điều khoản sử dụng
                  │
                  ▼
              Tài khoản ở trạng thái PENDING
                  │
                  ▼
         OWNER/ADMIN duyệt ──► Chọn cấp (OPERATOR hoặc ADMIN)
                  │
                  ▼
              Tài khoản ACTIVE ──► Truy cập Không gian điều hành
```

**Đăng nhập đã có tài khoản:**
```
Email + Mật khẩu ──► OTP Email ──► TOTP 2FA ──► Session (cookie HttpOnly)
```

### 2. Luồng cấp phép bay (Pi → PC → ESP32)

```
┌──────────────────────────────────────────────────────────────────────┐
│                      LUỒNG CẤP PHÉP BAY                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PHI CÔNG (trên Pi)              CÁN BỘ (trên PC)                   │
│                                                                      │
│  1. Đăng nhập Pi Wi-Fi AP       4. Nhận thông báo                   │
│     (192.168.4.1)                   có đơn bay mới                   │
│         │                              │                             │
│  2. Điền đơn xin bay:           5. Xem chi tiết đơn:                │
│     - Họ tên, bằng lái             - Vị trí GPS (bản đồ)           │
│     - Ngày giờ bay                  - Thông tin phi công             │
│     - Phương tiện                   - Phương tiện                    │
│         │                              │                             │
│  3. Pi mã hóa đơn bằng          6. Duyệt / Từ chối                 │
│     AES-256-GCM rồi gửi            + Nhập lý do                     │
│     lên PC server                      │                             │
│         │                              │                             │
│         ▼                              ▼                             │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │               PC SERVER (xử lý & lưu trữ)               │        │
│  │                                                         │        │
│  │  Giải mã phong bì ──► Lưu vào DB ──► Audit log         │        │
│  │  Kiểm tra replay   ──► Workflow FSM  ──► Trả kết quả   │        │
│  └─────────────────────────┬───────────────────────────────┘        │
│                             │                                        │
│  7. Pi nhận kết quả         ▼                                        │
│     từ PC server     ┌──────────────────┐                            │
│         │            │  Đơn APPROVED?   │                            │
│         ▼            └───┬──────────┬───┘                            │
│  ┌──────────────┐   YES │          │ NO                              │
│  │ $AUTH,ALLOW  │◄──────┘          └──────►┌──────────────┐          │
│  │ gửi xuống   │                           │ $AUTH,DENY   │          │
│  │ ESP32       │                           │ giữ ESP32    │          │
│  └──────┬───────┘                          │ bị BLOCKED   │          │
│         │                                  └──────────────┘          │
│         ▼                                                            │
│  8. ESP32 cho phép ARM                                               │
│     (phi công gạt công tắc)                                          │
│         │                                                            │
│  9. DRONE CẤT CÁNH ✈️                                               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3. Luồng Flight Gate (ESP32 — khóa ARM an toàn)

ESP32 khởi động ở trạng thái **BLOCKED**. Để ARM, phải thỏa mãn **tất cả** điều kiện theo thứ tự:

| # | Điều kiện | Biến | Lý do block nếu thiếu |
|---|-----------|------|----------------------|
| 1 | Đang nhận tín hiệu SBUS từ tay điều khiển | `rc_ok` | `RC_LOST` |
| 2 | Pi đã gửi `$AUTH,ALLOW` và còn hạn | `auth_allowed` | `NO_FLIGHT_AUTHORIZATION` |
| 3 | Pi còn sống (`$PING` trong 10s gần nhất) | `link_alive` | `PI_LINK_LOST` |
| 4 | GPS có fix (tùy cấu hình) | `gps_ok` | `NO_GPS_FIX` |
| 5 | Mode ở ANGLE | `mode_angle` | `MODE_NOT_ANGLE` |
| 6 | Đã thấy công tắc ARM ở vị trí DISARM trước | `arm_switch_seen_low` | `ARM_SWITCH_NOT_RESET` |
| 7 | Ga ở mức thấp (< 1050 µs) | `throttle_us` | `THROTTLE_HIGH` |
| 8 | Công tắc ARM đang ở vị trí ARM | `arm_switch_high` | `ARM_SWITCH_LOW` |

**Nguyên lý an toàn khi đang bay:**
- Chỉ **3 điều kiện** tắt motor giữa chuyến bay: gạt DISARM, mất RC, mode KILL.
- **Hết hạn cấp phép / mất Pi giữa chuyến bay KHÔNG cắt motor** — tránh rơi máy bay; chỉ chặn lần ARM kế tiếp.

### 4. Luồng giới hạn độ cao (Dynamic Altitude Limiter)

```
Drone vượt trần ──► Ghi nhớ mức ga hiện tại
       │
       ▼
Giảm dần trần ga (0.05 µs / 5ms = 10 µs/giây)
       │
       ▼
Floor động: max(1250, throttle - 150) µs, tối đa 1450 µs
       │
       ├── Tốc độ rơi > 0.4 m/s? ──► Nâng floor (vspeed damping)
       │                               Tránh rơi tự do
       │
       ├── Phi công kéo ga xuống? ──► Cho phép (pilot authority)
       │
       └── Hạ xuống dưới trần - 1m? ──► Tắt limiter, trả lại ga
```

### 5. Luồng Telemetry thời gian thực

```
ESP32                    Pi 5                      PC Server              PC Frontend
  │                        │                          │                       │
  │──$TELE,data──────────►│                          │                       │
  │  (UART 200ms)          │                          │                       │
  │                        │──AES-256-GCM sealed────►│                       │
  │                        │  POST /device/telemetry  │                       │
  │                        │                          │──Cache per-device───►│
  │                        │                          │                       │
  │                        │                          │◄──SSE /telemetry/──── │
  │                        │                          │    stream (1s)        │
  │                        │                          │                       │
  │                        │                          │  GPS, altitude,       │
  │                        │                          │  battery % ──────────►│
  │                        │                          │                   Leaflet map
  │                        │                          │                   marker update
```

---

## ✨ Tính năng

### Server PC (Backend + Frontend)

| Tính năng | Mô tả |
|-----------|-------|
| **Bản đồ vùng bay** | Leaflet + Geoman — vẽ/sửa/xóa vùng cấm bay (polygon), công khai hoặc nội bộ |
| **RBAC 4 cấp** | OWNER → ADMIN → OPERATOR → GUEST với phân quyền mịn |
| **Duyệt yêu cầu bay** | Workflow FSM: DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED/REJECTED |
| **Quản lý tài khoản** | Duyệt/từ chối/khóa tài khoản, đổi cấp quyền |
| **Telemetry thời gian thực** | SSE streaming GPS, altitude, battery — cập nhật < 2 giây |
| **Thông báo chuyến bay** | Badge + chime Web Audio khi có đơn bay mới |
| **Export dữ liệu** | GeoJSON (vùng bay) + CSV (lịch sử bay) — RFC 7946/4180 |
| **Dark mode** | Tự động theo system preference, WCAG AAA contrast 7.3:1 |
| **Loading states** | Skeleton/spinner với `aria-busy` khi tải dữ liệu |
| **Error handling** | Banner auto-dismiss 8 giây + nút đóng thủ công |
| **Audit trail** | Mọi thao tác được ghi vào `audit_events` + `workflow_history` |
| **Optimistic concurrency** | `version` field chống race condition khi cập nhật |
| **Idempotency** | `IdempotencyRecord` chống duplicate request |

### Pi 5 Gateway (Backend + Local Web UI)

| Tính năng | Mô tả |
|-----------|-------|
| **Giao diện cục bộ** | Web UI qua Wi-Fi AP (`192.168.4.1`), 11 ES modules |
| **Kết nối Wi-Fi** | Quét, chọn, nhập mật khẩu mạng Wi-Fi qua giao diện web |
| **Camera MJPEG** | Stream webcam USB, nút tạm dừng/tiếp tục tiết kiệm bandwidth |
| **Xin cấp phép bay** | Form đơn bay → mã hóa AES-256-GCM → gửi lên PC |
| **ESP32 Link** | UART/USB, gửi `$PING` mỗi 2 giây, nhận telemetry |
| **OTA Firmware** | Upload .bin ESP32, kiểm tra magic byte `0xE9`, khóa khi ARM |
| **Bản đồ vùng bay** | Leaflet + Three.js hiển thị vùng cấm từ PC server |
| **Quản lý người dùng** | Đăng ký, đăng nhập, phân quyền trên Pi |

### ESP32 Firmware (Flight Controller)

| Tính năng | Mô tả |
|-----------|-------|
| **PID Controller** | 3 vòng PID (angle → rate → motor) cho roll, pitch, yaw |
| **ICM20602 IMU** | Đọc gia tốc + gyroscope, bù nghiêng, Kalman filter |
| **BMP388 Barometer** | Đo độ cao, Kalman filter, tính vận tốc thẳng đứng |
| **GPS NMEA** | Parse NMEA 0183 v4.0, auto-detect pin (GPIO 16/17) |
| **SBUS RC** | Đọc tín hiệu điều khiển từ tay cầm RC |
| **Flight Gate** | Logic ARM/DISARM an toàn, testable C++ thuần |
| **Altitude Limiter** | Floor động 1250-1450 µs, vspeed damping, pilot authority |
| **Battery Monitor** | ADC chia áp, lọc EMA, tính % pin (tạm tắt chờ phần cứng) |
| **Link Protocol** | Giao tiếp Pi qua UART: `$PING`, `$AUTH`, `$TELE`, `$SET` |

---

## 🔒 Bảo mật

### Xác thực & Phiên đăng nhập

| Cơ chế | Chi tiết |
|--------|----------|
| **Mật khẩu** | Hash bằng **Argon2** (time=3, memory=64MB, parallelism=2) |
| **2FA bắt buộc** | TOTP (Google Authenticator compatible), chống replay với `totp_last_step` |
| **Session** | Token ngẫu nhiên 32 bytes, chỉ lưu **HMAC-SHA256 digest** trong DB |
| **CSRF** | Double-submit cookie pattern, kiểm tra header `X-CSRF-Token` |
| **OTP Email** | Mã 6 số, TTL 10 phút, tối đa 5 lần thử, gắn vào session cụ thể |
| **Recovery codes** | 8 mã dự phòng dạng hex, hash trước khi lưu |
| **Rate limiting** | IP-based: 10 login/15 phút, 20 đăng ký/15 phút, 5 OTP thử/challenge |

### Mã hóa dữ liệu

| Dữ liệu | Phương pháp |
|----------|-------------|
| **TOTP secret** | Mã hóa bằng Fernet (AES-128-CBC + HMAC-SHA256) |
| **Đơn bay (Pi → PC)** | Phong bì AES-256-GCM AEAD, AAD = `"{device_id}\|{timestamp}"` |
| **Chi tiết đơn bay** | Fernet-encrypted trong DB (`request_details_ciphertext`) |
| **Profile changes** | Mã hóa pending changes trong `changes_ciphertext` |

### Chống tấn công

| Tấn công | Biện pháp |
|----------|-----------|
| **Replay attack** | Cache nonce 600s TTL, timestamp skew ±300s |
| **Envelope tampering** | AEAD authenticated data, nonce kiểm tra 12 bytes |
| **Session fixation** | OTP login gắn vào session cụ thể (`session_id` FK) |
| **Email aliasing** | Gmail dot-stripping + subaddress `+tag` removal |
| **CSV injection** | Sanitize `=`, `+`, `-`, `@` trong CSV export |
| **CORS** | Whitelist origins, không cho phép `*` khi có cookies |
| **Brute force** | Rate limiter + Argon2 high cost + account lockout |

### An toàn bay (Firmware)

| Cơ chế | Chi tiết |
|--------|----------|
| **8 điều kiện ARM** | Phải thỏa mãn tất cả (xem bảng Flight Gate ở trên) |
| **Không cắt motor giữa bay** | Mất Pi / hết hạn chỉ chặn ARM kế tiếp |
| **Altitude limiter** | Floor động + vspeed damping, bảo toàn quyền phi công |
| **OTA lockout** | Cấm nạp firmware khi drone đang ARM |
| **PID lockout** | Cấm đổi PID khi đang ARM |
| **SBUS failsafe** | Phát hiện mất tín hiệu RC → DISARM ngay lập tức |

---

## 📁 Cấu trúc mã nguồn

```
IOT/
├── frontend/                    # PC Frontend (React 19 + TypeScript + Vite 7)
│   └── src/
│       ├── App.tsx              # App shell, routing, auth state
│       ├── api.ts               # API client (fetch wrapper)
│       ├── styles.css           # Design tokens + base styles
│       ├── experience.css       # Portal visual layer + dark mode
│       └── components/
│           ├── auth/AuthPanel.tsx           # Đăng nhập / đăng ký
│           ├── account/AccountMenu.tsx      # Menu tài khoản
│           ├── map/MapPanel.tsx             # Bản đồ Leaflet + Geoman
│           ├── operations/
│           │   ├── OperationsWorkspace.tsx  # Không gian điều hành
│           │   └── TelemetryPanel.tsx       # Telemetry thời gian thực
│           └── ErrorBanner.tsx             # Auto-dismiss error banner
│
├── server/                      # PC Backend (FastAPI + SQLAlchemy)
│   ├── app/
│   │   ├── config.py            # Settings từ env vars
│   │   ├── db.py                # SQLAlchemy engine + session
│   │   ├── models.py            # 14 ORM models (User, Zone, Flight...)
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── security.py          # Argon2, HMAC, TOTP, Fernet, email norm
│   │   ├── services.py          # Audit, zone seeding, capabilities
│   │   ├── mail.py              # Email: Fake, SMTP (async), Unconfigured
│   │   ├── geo.py               # GeoJSON validation
│   │   └── routers/
│   │       ├── auth.py          # Register, login, OTP, 2FA, profile
│   │       ├── accounts.py      # Account review, role changes
│   │       ├── zones.py         # CRUD zones + GeoJSON export
│   │       ├── flights.py       # Flight requests + CSV export
│   │       ├── device.py        # Device channel (sealed envelopes)
│   │       ├── telemetry.py     # Telemetry ingestion + SSE stream
│   │       └── misc.py          # Health check, terms
│   ├── migrations/              # Alembic migrations (8+)
│   └── data/app.db              # SQLite database
│
├── edge/pi5/                    # Raspberry Pi 5 Gateway
│   └── pi5/
│       ├── cli.py               # CLI: seed-admin, bootstrap
│       ├── network/
│       │   ├── nm.py            # NetworkManager (nmcli) adapter
│       │   ├── adapters.py      # Mock/Real network adapters
│       │   └── state.py         # Network state machine
│       ├── telemetry/
│       │   ├── esp_link.py      # UART/USB link with ESP32
│       │   ├── esp_command.py   # Command builder with checksum
│       │   └── gnss.py          # GNSS data adapter
│       └── web/
│           ├── app.py           # FastAPI app + routes
│           ├── asgi.py          # ASGI entry point
│           ├── authority.py     # Flight permission: Pi→PC→ESP32
│           ├── device_crypto.py # AES-256-GCM seal/open
│           ├── camera.py        # MJPEG stream + pause/resume
│           ├── firmware.py      # OTA: download, verify SHA-256, flash
│           └── ui/              # Local web interface
│               ├── index.html
│               ├── app.css
│               ├── app.js       # Entry point (imports modules)
│               ├── core/
│               │   ├── dom.js   # HyperScript DOM builder
│               │   └── api.js   # API client + CSRF
│               └── views/       # 8 domain views
│                   ├── wifi.js, auth.js, camera.js, map.js,
│                   ├── telemetry.js, users.js, firmware.js, flight.js
│                   └── vendor/  # Leaflet, Three.js (vendored)
│
├── firmware/FC_can_bang/        # ESP32 Flight Controller (C++)
│   ├── FC_can_bang.ino          # Main: setup, loop, ARM state machine
│   ├── flight_gate.h            # ARM logic + altitude limiter (pure C++)
│   ├── gps_nmea.h               # NMEA parser (pure C++)
│   ├── PID.ino                  # 3-axis PID controller
│   ├── ICM20602.ino             # IMU driver + Kalman filter
│   ├── Baro.ino                 # BMP388 barometer + Kalman
│   ├── GPS.ino                  # GPS UART reader, auto pin detect
│   ├── Sbus.ino                 # SBUS RC receiver
│   ├── ESCino.ino               # ESC PWM output
│   ├── Power.ino                # Battery ADC monitor
│   ├── Link.ino                 # UART protocol with Pi
│   ├── MODE.ino                 # Flight modes (angle, altitude limit)
│   └── display.ino              # OLED display output
│
├── contracts/v1/                # API contracts giữa các tầng
├── docs/                        # 20+ tài liệu kiến trúc + reports
├── tests/                       # Test suites
│   ├── scope01/                 # Auth flow, health, contracts
│   ├── scope02/                 # Account roles, flight workflow
│   ├── scope03/                 # Network (Pi Wi-Fi)
│   ├── scope04/                 # Pi web features
│   ├── scope05/                 # ESP32 telemetry, GNSS
│   ├── scope06/                 # Device channel, Pi authority
│   ├── scope07/                 # Firmware update
│   ├── firmware/                # C++ unit tests (flight_gate, GPS)
│   └── e2e/                     # 77 end-to-end tests (5 tiers)
└── ops/                         # Deployment scripts
```

---

## 🚀 Cài đặt & Triển khai

### Yêu cầu

| Component | Yêu cầu |
|-----------|---------|
| **PC Server** | Python 3.11+, Node.js 20+ |
| **Pi 5** | Raspberry Pi OS, Python 3.11+, Wi-Fi dongle |
| **ESP32** | Arduino IDE hoặc PlatformIO, ESP32 DevKit |

### PC Server

```bash
# 1. Clone & cài đặt dependencies
cd IOT
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows
pip install -r server/requirements.txt

# 2. Cấu hình biến môi trường
export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export ALLOWED_ORIGINS="http://localhost:5173"
export APP_ENV="development"

# 3. Khởi tạo database
cd server
alembic upgrade head

# 4. Chạy backend
uvicorn app.main:app --host 127.0.0.1 --port 8765

# 5. Chạy frontend (terminal khác)
cd frontend
npm install
npm run dev
```

### Pi 5

```bash
# 1. Cài đặt
cd edge/pi5
pip install -r pi5/requirements-scope04.lock

# 2. Cấu hình (xem ops/pi5/pi.env.example)
export PI_DEVICE_ID="<device-id-từ-PC>"
export PI_DEVICE_KEY="<32-byte-key>"
export PI_PC_MAP_URL="https://<pc-server>"

# 3. Khởi tạo admin
python -m pi5.cli seed-default-admin

# 4. Chạy
uvicorn pi5.web.asgi:app --host 0.0.0.0 --port 80
```

### ESP32

```bash
# Mở firmware/FC_can_bang/FC_can_bang.ino trong Arduino IDE
# Board: ESP32 Dev Module
# Upload speed: 921600
# Flash frequency: 80MHz
```

---

## ⚙ Biến môi trường

### PC Server

| Biến | Bắt buộc | Mặc định | Mô tả |
|------|----------|----------|-------|
| `SESSION_SECRET` | ✅ | — | Secret key cho HMAC token + Fernet encryption |
| `ALLOWED_ORIGINS` | ✅ | `https://localhost:5173` | CORS origins (comma-separated) |
| `APP_ENV` | | `development` | `development` / `test` / `production` |
| `DATABASE_URL` | | `sqlite:///server/data/app.db` | SQLAlchemy database URL |
| `HOST` | | `127.0.0.1` | Bind address |
| `PORT` | | `8765` | Bind port |
| `SMTP_HOST` | | — | SMTP server cho email OTP |
| `SMTP_PORT` | | `587` | SMTP port |
| `SMTP_USERNAME` | | — | SMTP username |
| `SMTP_PASSWORD` | | — | SMTP password |
| `SMTP_FROM` | | — | Sender email address |
| `COOKIE_SECURE` | | `true` | Set false cho HTTP (dev only) |
| `SEED_DEMO_DATA` | | `false` | Tạo dữ liệu mẫu khi khởi động |

### Pi 5

| Biến | Bắt buộc | Mô tả |
|------|----------|-------|
| `PI_DEVICE_ID` | ✅ | ID thiết bị đăng ký trên PC |
| `PI_DEVICE_KEY` | ✅ | AES-256 key (32 bytes, base64) |
| `PI_PC_MAP_URL` | ✅ | HTTPS URL của PC server |

---

## 🧪 Kiểm thử

```bash
# Chạy toàn bộ test suite
pytest tests/scope01 tests/scope02 tests/scope03 tests/scope04 \
       tests/scope05 tests/scope06 tests/scope07 tests/firmware -q

# Chạy E2E tests (77 tests, 5 tiers)
pytest tests/e2e/ -v

# Chạy frontend typecheck
cd frontend && npm run typecheck

# Chạy frontend build
cd frontend && npm run build
```

| Suite | Số tests | Phạm vi |
|-------|---------|---------|
| scope01 | 61 | Auth flows, health, contracts |
| scope02 | 28 | Account roles, flight workflow |
| scope03 | — | Pi network (nmcli) |
| scope04 | — | Pi web features |
| scope05 | 42 | ESP32 telemetry, GNSS |
| scope06 | — | Device channel, authority |
| scope07 | — | Firmware update |
| firmware | — | C++ unit tests (flight_gate, GPS NMEA) |
| e2e | 77 | End-to-end across all tiers |
| **Tổng** | **329+** | **100% PASS** |

---

## 📜 API Contracts

Xem chi tiết tại `contracts/v1/`:

| Contract | Mô tả |
|----------|-------|
| `DEVICE_FLIGHT_CONTRACT.md` | Giao thức Pi ↔ PC: sealed envelopes, flight requests |
| `SCOPE05_ESP32_TELEMETRY_CONTRACT.md` | Giao thức ESP32 ↔ Pi: UART commands |
| `SCOPE05_ESP32_USB_TELEMETRY_CONTRACT.md` | USB telemetry variant |
| `SCOPE04_PI_WEB_CONTRACT.md` | Pi local web API |
| `SCOPE03_PI_NETWORK_MOCK.md` | Pi network adapter contract |

---

## 📎 Phụ lục kỹ thuật

### Database Schema (14 models)

| Model | Bảng | Vai trò |
|-------|------|---------|
| `User` | `users` | Tài khoản: username, email, role, status, license |
| `Credential` | `credentials` | Password hash (Argon2), TOTP secret (Fernet) |
| `SessionRecord` | `sessions` | Token digest, CSRF, stage, TTL |
| `EmailChallenge` | `email_challenges` | OTP codes (hash), attempts, expiry |
| `ProfileUpdateChallenge` | `profile_update_challenges` | Pending profile changes (encrypted) |
| `RecoveryCode` | `recovery_codes` | Backup 2FA codes (hashed) |
| `TermsAcceptance` | `terms_acceptances` | Chấp nhận điều khoản sử dụng |
| `ZoneSource` | `zone_sources` | Nguồn dữ liệu vùng bay |
| `Zone` | `zones` | Vùng bay: geometry, classification, visibility |
| `AuditEvent` | `audit_events` | Log mọi thao tác (redacted metadata) |
| `RoleElevationRequest` | `role_elevation_requests` | Yêu cầu nâng cấp quyền |
| `Device` | `devices` | Pi device: name, encrypted key |
| `SimulatedFlightRequest` | `simulated_flight_requests` | Đơn xin bay (workflow FSM) |
| `IdempotencyRecord` | `idempotency_records` | Chống duplicate request |
| `WorkflowHistory` | `workflow_history` | Lịch sử thay đổi trạng thái |
| `CapabilityGrant` | `capability_grants` | Phân quyền mịn cho GUEST |

### UART Protocol (ESP32 ↔ Pi)

| Lệnh | Hướng | Mô tả |
|-------|-------|-------|
| `$PING,<seq>*<cs>` | Pi → ESP | Keepalive, mỗi 2 giây |
| `$AUTH,ALLOW*<cs>` | Pi → ESP | Cho phép ARM |
| `$AUTH,DENY*<cs>` | Pi → ESP | Cấm ARM |
| `$TELE,<data>*<cs>` | ESP → Pi | Telemetry: ARM state, GPS, altitude, battery |
| `$SET,<param>,<val>*<cs>` | Pi → ESP | Cấu hình PID, altitude max |

### Công nghệ sử dụng

| Tầng | Stack |
|------|-------|
| **Frontend** | React 19.2, TypeScript 5.9, Vite 7.3, Leaflet 1.9, QRCode |
| **Backend** | FastAPI, SQLAlchemy 2.x, Alembic, Argon2, PyOTP, Cryptography |
| **Pi Gateway** | FastAPI, NetworkManager (nmcli), v4l2-ctl, esptool |
| **Firmware** | Arduino/ESP32, ICM20602, BMP388, SBUS, NMEA 0183 |
| **Tests** | pytest, httpx (AsyncClient), C++ (g++ host build) |

---

## 📄 Giấy phép

Dự án nghiên cứu — mọi dữ liệu bản đồ chỉ mang tính tham khảo.

**© 2026 Phạm Ngọc Tấn & Phan Văn Đông**
