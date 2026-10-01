# SCOPE-00 — Yêu cầu sản phẩm và yêu cầu phi chức năng

Đây là nguồn sự thật cho requirement ID. Các scope khác liên kết về đây thay vì sao chép toàn bộ.

## Trạng thái và nhãn bằng chứng

`VERIFIED_FROM_SOURCE` = thấy trong archive/repository; `USER_REPORTED` = chủ dự án mô tả; `ASSUMPTION` = lựa chọn kiến trúc cần xác nhận; `UNVERIFIED` = cần đo/kiểm tra; `BLOCKED` = không thể kết luận trong ranh giới hiện tại.

## Chức năng

| ID | Yêu cầu | Miền | Trạng thái |
|---|---|---|---|
| REQ-PUB-01 | Guest chỉ đọc được lớp bản đồ công khai đã cho phép; không thấy dữ liệu cá nhân/nội bộ. | PC | `ASSUMPTION` |
| REQ-MAP-01 | Bản đồ pan/zoom/search, tọa độ, polygon, version, nguồn, thời điểm cập nhật. | PC | `USER_REPORTED` |
| REQ-MAP-02 | Lớp nghiên cứu nội bộ có CRUD, version và audit; không gắn nhãn pháp lý. | PC | `USER_REPORTED` |
| REQ-AUTH-01 | Đăng ký có email verification, TOTP enrollment và recovery codes. | PC/Pi | `USER_REPORTED` |
| REQ-AUTH-02 | Đăng nhập cần password + chấp thuận điều khoản + email OTP + TOTP theo policy; không bypass khi offline. | PC/Pi | `USER_REPORTED` |
| REQ-AUTH-03 | PC có `Owner`, `Admin`, `Operator`, `Pending`, `Guest`; Pi có `USER`, `ADMIN`; hai miền identity độc lập ở prototype. | PC/Pi | `ASSUMPTION` |
| REQ-WF-01 | Hồ sơ và duyệt/từ chối là workflow mô phỏng, có lịch sử và trạng thái gửi về Pi. | PC/Pi | `USER_REPORTED` |
| REQ-WF-02 | Kết quả workflow không tạo lệnh ARM/DISARM. | PC/Pi/ESP32 | `USER_REPORTED` |
| REQ-PI-NET-01 | Pi AP/recovery phát liên tục; current owner deployment profile uses onboard single-radio `ap0` AP + managed `wlan0` STA; LAN/local recovery remains available when upstream Internet fails. | Pi | `OWNER_OVERRIDE / LIVE_VALIDATION_PENDING` |
| REQ-PI-NET-02 | Hiển thị riêng `external_wifi_connected`, `internet_reachable`, `central_server_reachable`. | Pi | `USER_REPORTED` |
| REQ-PI-WEB-01 | Khi STA kết nối, client vẫn ở AP Pi và chuyển tới web Pi; không yêu cầu client đổi Wi-Fi. | Pi | `USER_REPORTED` |
| REQ-PI-01 | USER xem camera và gửi yêu cầu nâng quyền; ADMIN xem dashboard, bản đồ cache, telemetry, 3D, phiên/người dùng và firmware research area. | Pi | `USER_REPORTED` |
| REQ-TELEM-01 | Hiển thị chỉ trường ESP32 thực sự cung cấp; trường thiếu là `UNAVAILABLE`, không suy diễn. | Pi/ESP32 | `USER_REPORTED` |
| REQ-GNSS-01 | GNSS point kèm timestamp, fix/quality, accuracy/HDOP nếu có; stale marker; không có fix hợp lệ thì không tạo dữ liệu “hợp lệ”. | ESP32/Pi | `USER_REPORTED` |
| REQ-API-01 | API có version, auth, object-level authorization, idempotency và error envelope. | PC/Pi | `ASSUMPTION` |

## Phi chức năng, an toàn và pháp lý

| ID | Yêu cầu | Acceptance sơ bộ |
|---|---|---|
| NFR-SEC-01 | Không lưu plaintext password/OTP/TOTP/recovery code hoặc đưa secret vào log. | Static review + negative tests. |
| NFR-SEC-02 | Backend kiểm tra RBAC và ownership; UI không được là lớp bảo vệ duy nhất. | Test matrix 401/403/404. |
| NFR-SEC-03 | Session cookie có `Secure`, `HttpOnly`, `SameSite`; CSRF/rate limit/audit cho mutation. | Security test trước khi mở SCOPE-01. |
| NFR-OFF-01 | AP config/camera/dữ liệu nội bộ hoạt động khi Internet down. | Test bằng cách ngắt upstream ở lab, không ngắt thiết bị đang bay. |
| NFR-OFF-02 | Email OTP fail phải hiển thị trạng thái rõ và không tự hạ yêu cầu MFA. | E2E negative test. |
| NFR-SAF-01 | Không có server-to-flight-controller ARM path trong prototype. | Contract/schema scan và review sơ đồ. |
| NFR-LEGAL-01 | Tách rõ `SIMULATED / NOT A FLIGHT PERMIT`, dữ liệu nghiên cứu và nguồn pháp lý. | UI/API/docs review. |
| NFR-OPS-01 | Backup, restore, rollback, audit retention và stale data có kế hoạch trước public. | SCOPE-08 gate. |

## Traceability

REQ → module/API → scope → test/acceptance được lập tại [20_ACCEPTANCE_CRITERIA.md](20_ACCEPTANCE_CRITERIA.md) và [06_MODULE_BOUNDARIES.md](06_MODULE_BOUNDARIES.md).
