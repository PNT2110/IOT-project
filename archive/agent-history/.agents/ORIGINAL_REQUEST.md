# Original User Request

## 2026-09-09T13:05:46Z

# Teamwork Project Prompt — Draft

> Status: Ready for launch — awaiting user approval
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: [none — teamwork routes from the description]

The user wants to improve a drone station project running on a Raspberry Pi 5. The primary new task is to read GPS data (from a BZ251 via a CH340 USB TTL adapter) at a baud rate of 38400 and prepare to read ESP32 data via USB serial later.

Working directory: c:\Users\pnt21\OneDrive\Máy tính\IOT
Integrity mode: development

## Requirements

### R1. USB Serial Migration for GPS
Update the system to read GPS data from a USB serial port instead of the hardware GPIO UART (`/dev/serial0`). The GPS communicates at 38400 baud. 

### R2. Concurrent USB Device Handling
The system must be prepared to handle an ESP32 connected via USB alongside the GPS. Since both may use similar USB-to-TTL adapters (like CH340), the system must reliably distinguish and assign the correct serial stream to the GPS worker and ESP worker. The implementation approach (e.g. content-based auto-detect) is left to the team.

### R3. Overall Codebase Improvement
Perform a general review and improvement of the existing project codebase based on the context in `PROJECT_STATUS.md` and `WORKLOG.md`. Ensure the backend and frontend are robust and address any pending software blockers mentioned.

## Acceptance Criteria

### Verification
- [ ] Agent must write automated unit tests / mock tests (using pytest) to verify that the system correctly identifies and assigns USB ports for GPS and ESP32 when both are connected or simulated.
- [ ] The existing backend test suite (`pytest`) must pass completely.
- [ ] Code modifications must not break the current frontend-backend integrations.

## 2026-09-09T19:36:18Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: [none — teamwork routes from the description]

Nghiên cứu cấu trúc dữ liệu vùng cấm bay cũ trong dự án IOT (có thể là file JSON, GeoJSON, hoặc file mã nguồn chứa tọa độ), sau đó cập nhật lại hệ thống bản đồ cấm bay hiện tại (file `backend/data/zones.geojson` và giao diện `App.tsx`) để hiển thị dữ liệu y hệt bản cũ.

Working directory: c:\Users\pnt21\OneDrive\Máy tính\IOT
Integrity mode: development

## Requirements

### R1. Tìm và trích xuất dữ liệu cũ
- Quét toàn bộ thư mục `IOT` (và các thư mục liên quan) để tìm kiếm tệp dữ liệu vùng cấm bay cũ đã tồn tại trước đó.
- Phân tích định dạng tọa độ và cấu trúc của dữ liệu cũ.

### R2. Cập nhật dữ liệu vào hệ thống mới
- Cập nhật hệ thống backend (hoặc file `zones.geojson`) để áp dụng cấu trúc dữ liệu cũ vào.
- Nếu cần, cập nhật lại cách frontend (`App.tsx`) đọc và vẽ dữ liệu polygon lên MapLibre sao cho đúng với hình dáng và màu sắc của vùng cấm bay cũ.

## Acceptance Criteria

### Xác minh kết quả
- [ ] Backend API (`/api/v1/geofence/zones`) phải trả về đúng dữ liệu polygon lấy từ nguồn cũ.
- [ ] Frontend vẽ thành công các vùng cấm bay (prohibited) và hạn chế bay (restricted) lên bản đồ.
- [ ] Không có lỗi parse tọa độ (đảo ngược kinh độ/vĩ độ hoặc lỗi định dạng GeoJSON).

## 2026-09-13T09:30:16Z

# Teamwork Project Prompt — Draft

Nâng cấp toàn diện dự án IOT Drone Station (Raspberry Pi 5 + ESP32 + React) lên phiên bản v2 theo đặc tả trong `prompt-du-an-drone-v2.md`. 
Dự án bao gồm nhiều thành phần kết nối chặt chẽ với nhau, yêu cầu triển khai theo từng giai đoạn tuần tự.

Working directory: /home/pnt/IOT
Integrity mode: development

## Requirements

### R1. ESP32 Wi-Fi Provisioning
Viết lại logic ESP32 (`FC_can_bang`) để phát AP + captive portal chọn Wi-Fi khi chưa cấu hình, sau đó chuyển giao cho Pi5. Pi5 sử dụng systemd/bare-metal (không dùng Docker).

### R2. Hệ thống Tài khoản & Phân quyền Pi5
Xây dựng đăng ký/đăng nhập, xác thực 2FA TOTP, OTP qua email. Ép buộc admin (user `pi5`) phải đổi email và cài OTP trong lần đăng nhập đầu tiên.

### R3. Quản lý & Nạp Firmware ESP32
Xây dựng luồng nạp firmware bắt buộc trên Pi5. Chặn toàn bộ tính năng điều khiển cho tới khi firmware được nạp thành công.

### R4. Giao diện Admin 6 Tabs & Theme
Cập nhật React UI thành 6 tab: Camera, Telemetry+3D (thêm cao độ LiDAR), PID tuning, Session, Map, Quản lý FW. Áp dụng đồng bộ theme màu xanh-trắng trên cả UI và captive portal.

### R5. MOD Server & Fail-Safe ARM Locking
Xây dựng MOD server độc lập để cấp phép bay (theo tọa độ, bán kính, khung giờ). Khóa hoàn toàn lệnh ARM nếu chưa được duyệt, hoặc bay ngoài 1km, hoặc sai giờ. Tuân thủ tuyệt đối fail-safe: sai/thiếu dữ liệu -> khóa ARM. KHÔNG tự ý bật `ENABLE_REAL_FLIGHT_COMMANDS=true`.

### R6. Kiểm tra Bảo mật (Security Hardening)
Đổi mật khẩu mặc định, cấu hình SSH keys an toàn, kiểm tra các lỗ hổng theo mục 13 và xuất báo cáo rủi ro.

## Acceptance Criteria

### Verification & Testing
- [ ] Hoàn thành toàn bộ Checklist Definition of Done (mục 11).
- [ ] Chạy thành công 16 kịch bản kiểm thử trong bảng 12.1 qua SSH tự động, ghi log pass/fail rõ ràng.
- [ ] Xuất báo cáo bảo mật đầy đủ lỗ hổng, mức độ rủi ro và cách khắc phục.
- [ ] Liệt kê rõ các điểm giả định (assumptions) đã tự quyết định.

## 2026-09-13T20:45:54Z

# Teamwork Project Prompt — Draft

Nâng cấp toàn diện dự án IOT Drone Station (Raspberry Pi 5 + ESP32 + React) lên phiên bản v2 theo đặc tả trong `prompt-du-an-drone-v2.md`. 
Dự án bao gồm nhiều thành phần kết nối chặt chẽ với nhau, yêu cầu triển khai theo từng giai đoạn tuần tự.

Working directory: /home/pnt/IOT
Integrity mode: development

## Requirements

### R1. ESP32 Wi-Fi Provisioning
Viết lại logic ESP32 (`FC_can_bang`) để phát AP + captive portal chọn Wi-Fi khi chưa cấu hình, sau đó chuyển giao cho Pi5. Pi5 sử dụng systemd/bare-metal (không dùng Docker).

### R2. Hệ thống Tài khoản & Phân quyền Pi5
Xây dựng đăng ký/đăng nhập, xác thực 2FA TOTP, OTP qua email. Ép buộc admin (user `pi5`) phải đổi email và cài OTP trong lần đăng nhập đầu tiên.

### R3. Quản lý & Nạp Firmware ESP32
Xây dựng luồng nạp firmware bắt buộc trên Pi5. Chặn toàn bộ tính năng điều khiển cho tới khi firmware được nạp thành công.

### R4. Giao diện Admin 6 Tabs & Theme
Cập nhật React UI thành 6 tab: Camera, Telemetry+3D (thêm cao độ LiDAR), PID tuning, Session, Map, Quản lý FW. Áp dụng đồng bộ theme màu xanh-trắng trên cả UI và captive portal.

### R5. MOD Server & Fail-Safe ARM Locking
Xây dựng MOD server độc lập để cấp phép bay (theo tọa độ, bán kính, khung giờ). Khóa hoàn toàn lệnh ARM nếu chưa được duyệt, hoặc bay ngoài 1km, hoặc sai giờ. Tuân thủ tuyệt đối fail-safe: sai/thiếu dữ liệu -> khóa ARM. KHÔNG tự ý bật `ENABLE_REAL_FLIGHT_COMMANDS=true`.

### R6. Kiểm tra Bảo mật (Security Hardening)
Cấu hình SSH keys an toàn, kiểm tra các lỗ hổng theo mục 13 và xuất báo cáo rủi ro. Tuyệt đối KHÔNG được đổi password của user `pi5` (vẫn giữ nguyên là `123456`), và KHÔNG được tắt Password Authentication. Mạch Pi5 có IP là 192.168.1.118.

## Acceptance Criteria

### Verification & Testing
- [ ] Hoàn thành toàn bộ Checklist Definition of Done (mục 11).
- [ ] Chạy thành công 16 kịch bản kiểm thử trong bảng 12.1 qua SSH tự động, ghi log pass/fail rõ ràng.
- [ ] Xuất báo cáo bảo mật đầy đủ lỗ hổng, mức độ rủi ro và cách khắc phục.
- [ ] Liệt kê rõ các điểm giả định (assumptions) đã tự quyết định.

## 2026-09-14T05:07:21Z

# Teamwork Project Prompt — Draft

> Status: Ready for launch — awaiting user approval.
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: [none — teamwork routes from the description]

Khắc phục lỗi tồn đọng (Camera, Serial USB, Map) và điều chỉnh kiến trúc dự án IOT Drone Station v2 (Chuyển MOD Server sang Google Apps Script).

Working directory: /home/pnt/IOT
Integrity mode: development

## Requirements

### R1. Khắc phục lỗi Camera & Bản đồ
- **Camera:** Fix lỗi không hiển thị luồng video. Sử dụng Camera CSI/USB được cắm trực tiếp vào Raspberry Pi 5. Viết stream handler (ví dụ dùng OpenCV/v4l2) trên backend FastAPI để stream ra frontend.
- **Bản đồ:** Fix lỗi Map của Admin không hiện lên. Đảm bảo MapLibre GL có nguồn tile hợp lệ (offline hoặc public OSM) và load được UI.

### R2. Khắc phục kết nối Serial USB (Pi5 ⇄ ESP32)
- Sửa lỗi Pi5 không đọc được dữ liệu từ ESP32 qua cáp USB.
- Backend Python phải tự động quét các cổng `/dev/ttyUSB*` và `/dev/ttyACM*` để tìm ESP32 thay vì fix cứng, tự động kết nối lại nếu bị ngắt.

### R3. Luồng nạp Firmware tĩnh từ Nhà sản xuất
- Cập nhật giao diện và API nạp firmware: Xóa tính năng cho phép người dùng upload file `.bin` tùy ý.
- Hệ thống luôn đọc và nạp một file firmware chuẩn được lưu sẵn trên Pi5 (ví dụ: `/opt/drone-web-ui/firmware/official.bin` hoặc đường dẫn tương tự). Nếu không có file này, hệ thống cảnh báo và khóa ARM.

### R4. Điều chỉnh UI Đăng nhập
- Trên form đăng nhập, loại bỏ các chữ như "tài khoản pi5". Text hiển thị chỉ ghi ngắn gọn: "tên đăng nhập".

### R5. Di dời MOD Server sang Google Apps Script
- Thay thế local `mod_server.py` bằng một file mã nguồn Google Apps Script (tạo file `backend/mod_server.gs` để người dùng copy).
- File `.gs` phải implement `doGet()` hoặc `doPost()` xử lý cấp phép bay, tạo geofence 1km, trả về JSON.
- Cập nhật `backend/app/main.py` trên Pi5: Không gọi `localhost:9000` nữa mà gọi tới một URL được cấu hình trong file `.env` (ví dụ `MOD_WEBAPP_URL=...`). Viết logic để xử lý token/response từ Apps Script Web App.

## Acceptance Criteria

### Verification
- [ ] Giao diện Web hiển thị được video từ camera gắn trên Pi5.
- [ ] Tab bản đồ render thành công các lớp layer và marker, không bị trắng màn hình.
- [ ] Khi cắm ESP32 vào cổng USB/ACM bất kỳ, hệ thống Pi5 tự động nhận diện và parse được bản tin JSONL từ ESP32.
- [ ] Nút "Nạp Firmware" trên UI không mở hộp thoại chọn file, mà thực hiện nạp trực tiếp file `official.bin` từ ổ cứng Pi5.
- [ ] UI đăng nhập chỉ hiển thị "tên đăng nhập".
- [ ] Tồn tại file `backend/mod_server.gs` chứa code Google Apps Script hoàn chỉnh, có hướng dẫn Deploy (để sinh ra link `/exec`). Backend Pi5 gọi API tới biến môi trường `MOD_WEBAPP_URL` thành công (có thể mock URL này trong quá trình test của AI).
