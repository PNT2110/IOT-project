# BÁO CÁO KỸ THUẬT: NÂNG CẤP FRONTEND V2 & HỆ THỐNG 6 TAB (MILESTONE 5)

**Người thực hiện**: Frontend Worker (Milestone 5)  
**Thời điểm hoàn thành**: 13/09/2026  
**Thư mục làm việc**: `/home/pnt/IOT/.agents/worker_m5_frontend_r2`  
**Mã nguồn sở hữu**: `/home/pnt/IOT/frontend/src`  

---

## 1. TỔNG QUAN KẾT QUẢ TRIỂN KHAI

Toàn bộ ứng dụng web Single Page Application (React 19 + TypeScript + Vite) thuộc thư mục `frontend/` đã được nâng cấp toàn diện lên phiên bản v2 theo đúng đặc tả tại `prompt-du-an-drone-v2.md` (Mục 1, 5, 6, 8, 9, 10, 11) và bản khảo sát kỹ thuật `explorer_v2_survey_3`.

### Các kết quả then chốt đạt được:
1. **Hệ thống Theme Xanh — Trắng Hàng Không (Blue-White Aviation GCS)**:
   - Thay thế toàn bộ bảng màu tối cyberpunk đen-neon bằng hệ thống design tokens hiện đại, độ tương phản cao cho trạm mặt đất:
     - Nền tổng thể: `#f4f7fb` / `#ffffff`
     - Thẻ & Bảng điều khiển: `#ffffff` bo góc 12px, viền nhẹ `#e2e8f0`, đổ bóng mềm.
     - Màu chủ đạo Xanh Hàng không: Primary `#0066cc`, Hover `#0052a3`, Nền nhấn `#ebf3fc`.
     - Màu trạng thái ngữ nghĩa: An toàn `#16a34a`, Cảnh báo `#d97706`, Nguy hiểm/Khóa `#dc2626`.
     - Chữ Slate tương phản cao: `#0f172a` / `#475569`.
2. **Tổ chức 6 Tab Chức Năng Chuyên Biệt**:
   - **Tab 1: Camera (`CameraTab.tsx`)**:
     - Hiển thị luồng video trực tiếp USB Camera từ `/api/v1/camera/stream` (với cơ chế fallback, tự động kết nối lại).
     - Nút chụp ảnh nhanh (Snapshot) kèm OSD đóng dấu thời gian thực và tự động tải về file JPG.
     - Đồng hồ đo độ phân giải phát hiện (`1280 × 720 HD`) và tốc độ khung hình thực tế (`30 FPS`).
   - **Tab 2: Telemetry & Mô hình 3D (`TelemetryTab.tsx`)**:
     - Mô hình 3D tương tác Three.js / R3F chuyển động theo thời gian thực (5Hz) cho Roll, Pitch, Yaw.
     - Thẻ hiển thị **Cao độ cảm biến LiDAR (`lidar_altitude_m` / `Altitude_kalman`)** định dạng nổi bật với thước đo đồ họa bám đất 0-10m.
     - Các đồng hồ đo trực quan: Góc Roll (chân trời nhân tạo), Góc Pitch (độ chúi/ngửa), Góc Yaw (la bàn hướng mũi), Mức pin (Dung lượng % và Điện áp V).
   - **Tab 3: PID Tuning (`PidTuningTab.tsx`)**:
     - Nâng cấp từ chế độ chỉ đọc sang **điều khiển đọc/ghi 2 chiều tương tác serial**.
     - Đọc thông số hiện tại từ ESP32 qua `GET /api/v1/pid/config` (fallback `GET /api/v1/pid`).
     - Giao diện nhập liệu kiểm tra hợp lệ (validation: không âm, giới hạn an toàn Kp ≤ 15, Ki, Kd ≤ 5).
     - Nút **"Ghi xuống ESP32"** gửi lệnh `POST /api/v1/pid/config` kèm phản hồi thông báo ACK xác nhận.
     - Biểu đồ thời gian thực Recharts phản ánh đáp ứng tín hiệu đầu ra 3 trục Roll, Pitch, Yaw.
   - **Tab 4: Tài khoản đang đăng nhập (`SessionTab.tsx`)**:
     - Hiển thị hồ sơ người dùng: Họ và tên, Ngày sinh, Email, Vai trò (User / Admin), Trạng thái phê duyệt, Thời hạn phiên đăng nhập.
     - Bảng điều khiển riêng cho Admin mặc định: **"Quản lý duyệt Admin"** (`/api/v1/admin/pending-users`, `/api/v1/admin/approve-user`) cho phép phê duyệt hoặc từ chối tài khoản đăng ký mới.
     - Danh sách các phiên làm việc đang hoạt động và nút Đăng xuất an toàn.
   - **Tab 5: Bản đồ (`MapTab.tsx`)**:
     - Bản đồ MapLibre GL tích hợp nguồn PMTiles offline vector với giao diện tông màu sáng (Light Aviation).
     - Marker Drone GPS thời gian thực xoay theo góc hướng mũi (`course_deg` / `yaw`).
     - Tải và vẽ đầy đủ các đa giác vùng cấm bay (đỏ `#dc2626`) và vùng hạn chế bay (vàng `#d97706`).
     - **Vẽ vòng tròn nét đứt màu xanh lá cây bán kính 1km (1000m)** khi giấy phép bay được MOD phê duyệt, kèm widget thông tin nổi đếm thời gian bay hợp lệ.
   - **Tab 6: Quản lý Firmware (`FirmwareTab.tsx`)**:
     - Huy hiệu trạng thái Firmware: `ĐÃ NẠP (SẴN SÀNG)` / `CHƯA NẠP (BỊ KHÓA)` / `ĐANG NẠP`.
     - Khu vực kéo thả hoặc chọn tệp nhị phân `.bin` với tính toán mã băm SHA-256 trực tiếp.
     - Nút **"Nạp Firmware vào ESP32"** (`POST /api/v1/firmware/flash`) với thanh tiến trình nhiều bước (Xóa bộ nhớ -> Ghi nhị phân -> Xác thực mã băm -> Hoàn tất).
     - Nút xóa firmware với modal xác nhận cảnh báo.
     - Banner cảnh báo an toàn: **Khóa tuyệt đối tính năng ARM khi firmware chưa nạp!**
3. **Thanh Header & Modal "Xin phép bay"**:
   - Header hiển thị Drone ID (`DRONE-PI5-001`), GPS Status (`GPS LIVE` / `NO FIX`), ARM Status (`ARM KHÓA` / `SẴN SÀNG`).
   - Nút **"Xin phép bay (MOD)"** đặt trang trọng trên Header, **chỉ hiển thị cho tài khoản Admin đã được phê duyệt**.
   - Hộp thoại Modal thu thập đầy đủ:
     * Họ và tên người điều khiển (tự động điền theo session).
     * Mã bằng lái bay (`license_id`).
     * Ngày bay (`flight_date`).
     * Khung giờ bay (`time_from` đến `time_to`).
     * Tọa độ GPS drone hiện tại (tự động cập nhật từ telemetry với nút "Lấy tọa độ GPS Live").
   - Gửi yêu cầu qua `POST /api/v1/flight-request/submit` (chuyển tiếp MOD server) và hiển thị trạng thái phê duyệt trực quan.
4. **Phân quyền truy cập theo vai trò (Role-Based Restriction)**:
   - Khi đăng nhập với vai trò `user`: **CHỈ hiển thị Tab 1 (Camera) và Tab Thông tin tài khoản (Session)**. Các Tab 2, 3, 5, 6 và nút "Xin phép bay" hoàn toàn bị ẩn và chặn truy cập.
   - Khi tài khoản `admin` đang chờ duyệt (`approval_status: 'pending'`): Hiển thị banner cảnh báo và áp dụng cơ chế giới hạn tương tự User (chỉ xem Camera).

---

## 2. DANH MỤC TỆP NGUỒN ĐÃ TẠO VÀ CHỈNH SỬA

| Đường dẫn tệp | Loại thay đổi | Mô tả chức năng |
|---|---|---|
| `frontend/src/types.ts` | Cập nhật | Bổ sung LiDAR altitude, FlightPermission, PidConfig, FirmwareStatus, ActiveSession, PendingAdminUser |
| `frontend/src/api.ts` | Cập nhật | Bổ sung API wrappers cho PID tuning, firmware flash/upload/delete, sessions, admin user approval, flight request submit |
| `frontend/src/CameraTab.tsx` | Tạo mới | Tab 1: Luồng video trực tiếp USB camera, chụp ảnh snapshot, chỉ số FPS & độ phân giải |
| `frontend/src/TelemetryTab.tsx` | Tạo mới | Tab 2: Mô hình 3D Three.js, hiển thị nổi bật cao độ LiDAR (m), đồng hồ Roll/Pitch/Yaw/Heading/Battery |
| `frontend/src/PidTuningTab.tsx` | Tạo mới | Tab 3: Điều khiển đọc/ghi serial PID 2 chiều, validation, nút ghi xuống ESP32 với ACK, biểu đồ Recharts |
| `frontend/src/SessionTab.tsx` | Tạo mới | Tab 4: Hồ sơ người dùng, bảng duyệt Admin của default admin, danh sách phiên đăng nhập |
| `frontend/src/MapTab.tsx` | Tạo mới | Tab 5: MapLibre GL Light, vùng cấm bay, vòng tròn cấp phép bay 1km nét đứt màu xanh lá, GPS marker có góc quay |
| `frontend/src/FirmwareTab.tsx` | Tạo mới | Tab 6: Trạng thái firmware, upload widget `.bin`, nút nạp firmware với thanh tiến trình, banner khóa an toàn |
| `frontend/src/FlightPermissionModal.tsx` | Tạo mới | Hộp thoại modal xin phép bay gửi lên MOD Server |
| `frontend/src/Tabs.tsx` | Cập nhật | Bộ khung điều hướng 6 tab và thực thi phân quyền role |
| `frontend/src/SetupAccount.tsx` | Cập nhật | Giao diện thiết lập lần đầu cho Admin (email, mật khẩu, TOTP 2FA) theo theme Xanh — Trắng |
| `frontend/src/App.tsx` | Cập nhật | Khung ứng dụng chính, Header v2, Drone ID, status pills, nút xin phép bay, tích hợp 6 tab |
| `frontend/src/styles.css` | Cập nhật | Hệ thống theme Xanh — Trắng hàng không toàn diện, responsive CSS |

---

## 3. KẾT QUẢ BIÊN DỊCH VÀ XÁC MINH

Lệnh thực hiện:
```bash
export PATH="/home/pnt/IOT/node-v20.11.1-linux-x64/bin:$PATH" && cd /home/pnt/IOT/frontend && npm run build
```

Kết quả:
```text
> iot-drone-station-ui@0.1.0 build
> tsc -b && vite build

vite v7.3.6 building client environment for production...
✓ 2824 modules transformed.
dist/index.html                     0.55 kB │ gzip:   0.34 kB
dist/assets/index-CNcmadGi.css    107.04 kB │ gzip:  16.48 kB
dist/assets/index-mqB5OaZw.js   2,670.03 kB │ gzip: 740.40 kB
✓ built in 6.08s
```
- Mã thoát (Exit Code): **0**
- Lỗi TypeScript: **0 lỗi**
- Gói sản phẩm được tạo đầy đủ và toàn vẹn tại `frontend/dist/`.
