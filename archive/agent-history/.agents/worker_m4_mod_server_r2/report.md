# BÁO CÁO KỸ THUẬT TRIỂN KHAI MILESTONE 4: MÁY CHỦ BỘ QUỐC PHÒNG (MOD SERVER) ĐỘC LẬP

**Kỹ sư thực hiện**: MOD Server Worker (Milestone 4)  
**Ngày hoàn thành**: 13/09/2026  
**Thư mục làm việc**: `/home/pnt/IOT/.agents/worker_m4_mod_server_r2`  
**Mã nguồn triển khai**: `/home/pnt/IOT/backend/mod_server.py`  
**Bộ kiểm thử tích hợp**: `/home/pnt/IOT/backend/tests/test_mod_server.py`  

---

## 1. TỔNG QUAN KIẾN TRÚC HỆ THỐNG

Tuân thủ nghiêm ngặt đặc tả tại **Mục 7, 8, 10, 11 và 13** của `prompt-du-an-drone-v2.md`, máy chủ Bộ Quốc Phòng (MOD Server) được thiết kế và triển khai thành công dưới dạng một ứng dụng FastAPI độc lập, hoạt động tại cổng **9000** với cơ sở dữ liệu SQLite chuyên dụng ở chế độ WAL (`PRAGMA journal_mode=WAL;`).

### Các thông số cốt lõi:
1. **Cổng dịch vụ**: `9000` (truy cập đa mạng LAN / WAN, kích hoạt CORS `allow_origins=["*"]`).
2. **Cơ sở dữ liệu**: SQLite WAL (`backend/mod_database.sqlite3`), đảm bảo khả năng đọc ghi đồng thời cao mà không bị khóa cơ sở dữ liệu.
3. **Mã hóa & Bảo mật**:
   - Mật khẩu được băm bằng thuật toán `PBKDF2-HMAC-SHA256` (100.000 vòng lặp) kết hợp muối ngẫu nhiên (salt 16-byte).
   - Cơ chế chống tấn công phát lại (Anti-Replay): Yêu cầu bay được kiểm soát lệch thời gian tối đa `+/- 300 giây` và theo dõi tính duy nhất của giá trị `nonce`.
4. **Tài khoản mặc định được khởi tạo tự động**:
   - `admin_mod` (mật khẩu `ModAdmin2026!`, vai trò `admin`, trạng thái `APPROVED`).
   - `mod_admin` (mật khẩu `ModAdmin2026!` / `ModAdmin123!`, vai trò `admin`, trạng thái `APPROVED`).

---

## 2. CHI TIẾT CÁC PHÂN HỆ VÀ API ĐÃ TRIỂN KHAI

### 2.1 Quản lý tài khoản & Duyệt đăng ký (Mục 7.1)
- `POST /api/v1/mod/auth/register`: Tiếp nhận đăng ký tài khoản cán bộ/người điều khiển UAV mới. Mặc định gán trạng thái `PENDING`.
- `POST /api/v1/mod/auth/login`: Xác thực đăng nhập. **Bắt buộc chặn bằng mã 403 Forbidden** đối với tài khoản chưa được Quản trị viên Bộ Quốc Phòng phê duyệt (`PENDING` hoặc `REJECTED`).
- `GET /api/v1/mod/admin/pending-users` & `GET /api/v1/mod/admin/users`: Danh sách tài khoản người dùng kèm bộ lọc trạng thái.
- `POST /api/v1/mod/admin/users/{user_id}/approve` & `POST /api/v1/mod/admin/approve-user`: Admin MOD phê duyệt tài khoản, kích hoạt quyền đăng nhập và cấp phát JWT token.
- `POST /api/v1/mod/admin/users/{user_id}/reject`: Admin MOD từ chối tài khoản.

### 2.2 Luồng cấp phép bay & Thuật toán Geofence 1km (Mục 7.2 & 7.3)
- `POST /api/v1/mod/flight-requests`: Tiếp nhận hồ sơ xin phép bay gồm: `drone_id`, `pilot_name`, `license_id`, `flight_date`, `time_from`, `time_to`, `latitude`, `longitude`, `timestamp`, `nonce`.
  - Kiểm tra lệch thời gian: Nếu `abs(now - timestamp) > 300s` -> trả về `403 Forbidden` (`Timestamp deviation exceeded 300s window`).
  - Kiểm tra nonce trùng lặp: Nếu `nonce` đã tồn tại trong bảng `mod_used_nonces` -> trả về `403 Forbidden` (`Nonce already used`).
  - Khởi tạo yêu cầu ở trạng thái `PENDING` kèm mã yêu cầu định danh (ví dụ `REQ-0001`).
- `GET /api/v1/mod/flight-requests` & `GET /api/v1/mod/admin/requests`: Liệt kê các yêu cầu bay phục vụ bảng quản trị.
- `POST /api/v1/mod/flight-requests/{id}/approve` & `POST /api/v1/mod/admin/requests/{id}/approve`:
  - Phê duyệt yêu cầu bay.
  - Tự động sinh đa giác hình tròn Geodesic 64 đỉnh trên mô hình elip WGS84 với bán kính đúng `1000m` (+/- 20m) bao quanh tọa độ `(latitude, longitude)`.
  - Cấp mã giấy phép bay `permission_token` (định dạng `MOD-YYYYMMDD-REQxxxx`).
  - Thiết lập khung giờ hiệu lực: `valid_from = flight_date + T + time_from + :00Z`, `valid_to = flight_date + T + time_to + :00Z`.
- `POST /api/v1/mod/flight-requests/{id}/reject`: Đánh dấu từ chối yêu cầu bay.
- `GET /api/v1/mod/flight-requests/{drone_id}/active`:
  - Endpoint để trạm Pi5 kiểm tra trạng thái giấy phép bay theo chu kỳ.
  - Tự động kiểm tra thời gian: Nếu thời điểm hiện tại vượt quá `valid_to`, chuyển trạng thái yêu cầu sang `EXPIRED`, trả về `armed_allowed: false` để khóa hoàn toàn lệnh cất cánh ARM trên Pi5 / ESP32.
  - Nếu hợp lệ: Trả về trạng thái `APPROVED`, `armed_allowed: true`, tâm vùng bay, bán kính 1000m và GeoJSON đa giác vùng bay.

### 2.3 Quản lý Vùng cấm bay (No-Fly Zones) (Mục 7.2)
- `GET /api/v1/mod/zones` & `GET /api/v1/mod/geofence/zones`: Trả về GeoJSON `FeatureCollection` tổng hợp gồm:
  1. Các hành lang bay 1km đang được cấp phép và còn hiệu lực (`type: approved_zone`, viền nét đứt xanh dương).
  2. Các vùng cấm bay cố định hoặc tạm thời (`type: prohibited` - màu đỏ hoặc `type: restricted` - màu vàng cam).
- `POST /api/v1/mod/zones` & `POST /api/v1/mod/admin/zones`: Thêm mới đa giác vùng cấm bay (lưu vào bảng `mod_geofence_zones`).
- `DELETE /api/v1/mod/zones/{id}`: Xóa vùng cấm bay khỏi cơ sở dữ liệu.

### 2.4 Giao diện Web Quản trị Nhúng (Embedded Admin Dashboard)
- Cung cấp trực tiếp tại URL gốc `GET /` trên cổng 9000.
- Tuân thủ thiết kế **Xanh — Trắng (Blue-White Aviation Theme)** theo Mục 3.2 của đặc tả:
  - Header xanh biển đậm `#1e3a8a` - `#2563eb`, thẻ thông tin nền trắng `#ffffff` bo góc 12px, nền trang xám sáng `#f8fafc`.
  - **Tab 1: Tài khoản & Yêu cầu bay**:
    * 4 thẻ thống kê trực quan (Tổng yêu cầu, Chờ duyệt, Hành lang 1km đang mở, Tài khoản chờ duyệt).
    * Bảng danh sách tài khoản chờ duyệt với 2 nút thao tác nhanh: **Duyệt (Approve)** và **Từ chối (Reject)**.
    * Bảng danh sách yêu cầu bay với các bộ lọc trạng thái, hiển thị tọa độ GPS, khung giờ bay và nút **Duyệt 1km** (Approve 1km).
  - **Tab 2: Bản đồ & Vùng cấm bay**:
    * Tích hợp bản đồ tương tác Leaflet (OpenStreetMap / Carto tiles).
    * Hiển thị trực quan các hành lang bay 1km được duyệt và các vùng cấm đỏ/vàng.
    * Công cụ vẽ vùng cấm tương tác: Cho phép click chọn các điểm đỉnh trên bản đồ, xem trước đa giác, đặt tên vùng cấm, chọn loại vùng (Cấm bay / Hạn chế) và lưu trực tiếp về máy chủ.
    * Danh sách vùng cấm kèm nút **Xóa (Delete)** cập nhật tức thời trên bản đồ.
  - Cơ chế tự động đồng bộ: Tự động tải lại dữ liệu sau mỗi 6 giây mà không cần F5 trình duyệt.

---

## 3. KẾT QUẢ KIỂM THỬ VÀ XÁC MINH

### 3.1 Kiểm thử Đơn vị & Tích hợp (`backend/tests/test_mod_server.py`)
Đã thực thi bằng `pytest` với 7 kịch bản toàn diện:
1. `test_01_health_and_root_ui`: Xác minh endpoint `/health` và giao diện HTML Web UI tại `/` (24KB đầy đủ script & style). **PASSED**.
2. `test_02_default_admin_login`: Xác minh đăng nhập của `admin_mod` và `mod_admin`. **PASSED**.
3. `test_03_user_registration_and_approval_workflow`: Xác minh đăng ký tài khoản, chặn đăng nhập 403 khi PENDING, admin duyệt và đăng nhập thành công. **PASSED**.
4. `test_04_flight_permission_request_anti_replay`: Xác minh tạo yêu cầu bay, chặn replay duplicate nonce (403), chặn timestamp cũ lệch > 300s (403). **PASSED**.
5. `test_05_flight_approval_and_1km_geofence_zone`: Xác minh admin duyệt, tự động sinh đa giác 64 đỉnh, kiểm tra khoảng cách geodesic từ tâm tới các đỉnh đạt 980m - 1020m (chính xác ~1000m). **PASSED**.
6. `test_06_flight_window_expiry_and_arm_lock`: Xác minh tự động hết hạn và trả về `status: EXPIRED`, `armed_allowed: false`. **PASSED**.
7. `test_07_no_fly_zone_management`: Xác minh tạo vùng cấm, kiểm tra danh sách GeoJSON, xóa vùng cấm. **PASSED**.

**Kết quả**: `7 passed in 0.37s`.

### 3.2 Kiểm thử trực tiếp máy chủ hoạt động (Live HTTP trên cổng 9000)
Khởi chạy dịch vụ thực tế `uvicorn backend.mod_server:app --host 0.0.0.0 --port 9000`:
- Khởi tạo SQLite WAL `backend/mod_database.sqlite3` thành công.
- Tất cả request thực tế kiểm thử từ client đều đạt mã phản hồi chính xác (200, 201, 403) và dữ liệu chuẩn cấu trúc.

### 3.3 Kiểm thử Bộ Test Runner E2E (`tests/ssh_test_runner.py --mode=bench`)
Chạy kiểm thử 4 kịch bản liên quan đến MOD Server:
- **Scenario 10**: *Flight permission request to MOD server (GPS, time window, license)* -> **PASS (0.00s)**.
- **Scenario 11**: *Flight permit approval opens 1km radius zone* -> **PASS (0.01s)**.
- **Scenario 15**: *MOD server registration requires admin approval* -> **PASS (0.00s)**.
- **Scenario 16**: *Draw & delete no-fly zones (geofence engine update)* -> **PASS (0.01s)**.

---

## 4. KẾT LUẬN
Milestone 4 (M4: Independent Standalone MOD Server) đã hoàn thành xuất sắc 100% các yêu cầu nghiệp vụ, bảo mật và giao diện, sẵn sàng phục vụ tích hợp với trạm mặt đất Raspberry Pi 5 và FC ESP32.
