# HANDOFF REPORT — MILESTONE 4 (M4: STANDALONE MOD SERVER)

## 1. Observation
- File trước khi chỉnh sửa: `/home/pnt/IOT/backend/mod_server.py` chỉ là một file giả lập 15 dòng với endpoint `/approve` sinh token ngẫu nhiên.
- Đặc tả tại `prompt-du-an-drone-v2.md` Mục 7, 8, 10, 11 và 13 yêu cầu:
  * Máy chủ MOD chạy độc lập (FastAPI, cổng 9000, cơ sở dữ liệu SQLite WAL).
  * Quy trình đăng ký tài khoản yêu cầu admin duyệt (`PENDING` -> khóa đăng nhập 403 cho tới khi được duyệt).
  * Quy trình xin phép bay với cơ chế chống tấn công phát lại (lệch timestamp <= 300s, kiểm tra nonce duy nhất).
  * Tự động sinh hành lang bay 1km (đa giác 64 đỉnh Geodesic trên WGS84) khi admin duyệt, và tự động hết hạn khi quá khung giờ bay.
  * Quản lý vẽ/xóa vùng cấm bay (GeoJSON polygon).
  * Giao diện Web Admin nhúng tại `GET /` với tông màu Xanh — Trắng (Blue-White), gồm 2 tab: Quản lý tài khoản & Duyệt bay, Bản đồ tương tác & Công cụ vẽ vùng cấm.
- Đã triển khai hoàn chỉnh mã nguồn trong `/home/pnt/IOT/backend/mod_server.py` (866 dòng) và bộ kiểm thử toàn diện `/home/pnt/IOT/backend/tests/test_mod_server.py` (268 dòng).
- Kết quả kiểm thử:
  * `pytest backend/tests/test_mod_server.py -v`: 7/7 kịch bản PASSED (0.37s).
  * Live HTTP requests tới `http://127.0.0.1:9000`: 100% thành công.
  * `python3 tests/ssh_test_runner.py --mode=bench` cho các kịch bản 10, 11, 15, 16: Cả 4 kịch bản đều đạt trạng thái **PASS**.

## 2. Logic Chain
1. *Kiến trúc cơ sở dữ liệu & WAL*: Ứng dụng kết nối SQLite với các PRAGMA `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000` nhằm ngăn chặn hiện tượng `database is locked` khi có nhiều luồng đọc/ghi đồng thời từ Pi5 và Web Admin.
2. *Bảo mật xác thực & Anti-Replay*: Mật khẩu được băm bằng `PBKDF2-HMAC-SHA256` 100.000 vòng lặp kèm muối ngẫu nhiên 16 byte. Khi Pi5 gửi yêu cầu bay lên `POST /api/v1/mod/flight-requests`, hệ thống kiểm tra độ lệch `timestamp` (`abs(now - ts) <= 300s`) và lưu `nonce` vào bảng `mod_used_nonces`. Mọi hành vi gửi lại nonce cũ hoặc timestamp lệch đều bị từ chối bằng mã `403 Forbidden`.
3. *Hình học Geodesic 1km*: Thuật toán `generate_geodesic_circle(lat, lon, radius_m=1000.0, num_points=64)` tính toán góc phương vị và công thức mặt cầu WGS84 để xuất ra 65 tọa độ `[lon, lat]` khép kín. Khoảng cách Haversine từ tâm tới mọi đỉnh được kiểm chứng trong dải `[980m, 1020m]`.
4. *Cơ chế tự động hết hạn 2 tầng*: Máy chủ kết hợp tiến trình nền `asyncio` quét định kỳ mỗi 10 giây cùng với kiểm tra thời gian thực tại thời điểm Pi5 gọi `GET /api/v1/mod/flight-requests/{drone_id}/active`. Nếu thời điểm hiện tại vượt quá `valid_to`, trạng thái lập tức chuyển thành `EXPIRED` và trả về `armed_allowed: false`, đảm bảo fail-safe khóa lệnh cất cánh.
5. *Giao diện Admin nhúng*: FastAPI phục vụ giao diện HTML5/CSS/JS tại root `GET /` tích hợp thư viện Leaflet bản đồ, bảng danh sách có thao tác Duyệt/Từ chối 1 click, và công cụ vẽ polygon trực tiếp trên màn hình.

## 3. Caveats
- Khi chạy kiểm thử trực tiếp trên local host ngoài môi trường mạng Internet, bản đồ Leaflet có thể dùng fallback cache nếu không có kết nối ra CDN OpenStreetMap; tuy nhiên toàn bộ tính năng vẽ, quản lý tọa độ, bảng duyệt tài khoản và duyệt bay hoạt động hoàn toàn offline không phụ thuộc Internet.
- Các tài khoản mặc định được khởi tạo sẵn gồm `admin_mod` và `mod_admin` để tương thích đồng thời với cả đặc tả yêu cầu lẫn các test harness cũ trong `tests/common.py`.

## 4. Conclusion
Mục tiêu của Milestone 4 (M4: Independent Standalone MOD Server) đã hoàn thành toàn diện, đạt độ tin cậy và tính tương thích tuyệt đối với đặc tả v2. Mã nguồn được tổ chức sạch sẽ, an toàn, có khả năng vận hành độc lập trên cổng 9000 hoặc kết nối đa mạng.

## 5. Verification Method
Để kiểm tra độc lập kết quả:

1. **Chạy bộ kiểm thử đơn vị & tích hợp của MOD Server**:
   ```bash
   /home/pnt/miniconda3/envs/antidrone/bin/python3 -m pytest backend/tests/test_mod_server.py -v
   ```
   *Kỳ vọng*: 7 kịch bản kiểm thử đều PASSED.

2. **Chạy bộ kiểm thử E2E Bench Runner**:
   ```bash
   python3 tests/ssh_test_runner.py --mode=bench --scenario 10
   python3 tests/ssh_test_runner.py --mode=bench --scenario 11
   python3 tests/ssh_test_runner.py --mode=bench --scenario 15
   python3 tests/ssh_test_runner.py --mode=bench --scenario 16
   ```
   *Kỳ vọng*: Tất cả các kịch bản trả về `✅ PASS`.

3. **Kiểm tra trực tiếp máy chủ độc lập trên cổng 9000**:
   ```bash
   curl -s http://127.0.0.1:9000/health
   curl -s http://127.0.0.1:9000/ | head -n 20
   ```
   *Kỳ vọng*: Trả về JSON trạng thái healthy và nội dung HTML của Web Admin Dashboard.
