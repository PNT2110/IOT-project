# Yêu cầu của chủ dự án — 2026-10-01

Ghi lại từ yêu cầu trong phiên làm việc (đã bỏ dòng chứa mật khẩu máy).

## Chung

Chia dự án thành nhiều cụm module để dễ phát triển. Tự viết code, tự test,
triển khai trên máy PC và trên Pi; lưu chính ở PC, Pi chỉ giữ phần của Pi. Test
xong dọn sạch file test, chỉ để lại báo cáo.

## Máy chủ (PC hiện tại, công khai)

- Web có bản đồ kiểu Google Maps; vẽ, xóa, chỉnh sửa vùng cấm bay và hạn chế bay.
- Tab duyệt các yêu cầu xin phép bay. Tab duyệt các tài khoản đăng ký xin quyền.
- Chưa đăng nhập hoặc đăng ký: chỉ xem bản đồ có vẽ sẵn vùng cấm bay, không làm được gì khác.
- Đăng nhập: tài khoản, mật khẩu, tích xác nhận đã đọc điều khoản → OTP mail → mã 2FA.
- Đăng ký: tên, mail, mật khẩu, nhập lại mật khẩu → mã xác nhận mail → mã 2FA, yêu cầu người dùng lưu lại.
- Tài khoản chính đầu tiên được cấp mặc định: mã 2FA mặc định, không xác nhận mail.
- Người đăng ký phải chờ tài khoản chính duyệt. Hai cấp: cấp 1 admin được duyệt và nâng cấp; cấp 2 chỉ chỉnh sửa vùng cấm bay và duyệt bay, không duyệt tài khoản.

## Web trên Pi 5

- Pi phát Wi-Fi liên tục; vào Wi-Fi của Pi thì tự mở web mặc định.
- Giao diện 1: Pi chưa có Wi-Fi ngoài (qua USB) thì hiện giao diện kết nối Wi-Fi; kết nối xong hoặc đã có mạng thì sang giao diện 2.
- Giao diện 2: buộc đăng nhập hoặc đăng ký, luồng giống máy chủ.
- Tài khoản mặc định: 2FA mặc định, không xác nhận mail; khi đăng nhập phải điền thêm email, các lần sau vẫn xác thực OTP mail.
- Hai cấp user và admin; đăng ký đều là user; chỉ admin duyệt hoặc nâng user lên.
- User: đăng nhập xong chỉ xem camera từ webcam USB của Pi; thanh trên cùng có nút xin cấp quyền admin, gửi xong chờ admin cấp.
- Admin: tab 1 webcam USB; tab 2 bản đồ vùng cấm bay (lấy từ API máy chủ, không chỉnh sửa) và định vị hiện tại; tab 3 thông số drone (độ cao baro, góc nghiêng, % pin, nhiệt độ), tinh chỉnh (độ cao tối đa, PID), tín hiệu tay điều khiển, mô hình 3D theo dữ liệu ESP; tab 4 ai đang hoạt động và duyệt tài khoản lên admin; tab 5 cập nhật firmware từ nhà sản xuất để nạp cho drone.
- Thanh trên cùng có nút xin cấp phép bay: form họ tên đầy đủ, mã bằng lái, ngày bay, giờ bay, chọn phương tiện bay. Bấm gửi thì mã hóa và gửi toàn bộ kèm định vị GPS từ ESP lên máy chủ. Máy chủ duyệt hoặc không; duyệt thì trả lệnh duyệt về Pi, không thì trả lệnh từ chối. Được duyệt thì gửi lệnh arm xuống; không được duyệt thì gửi lệnh để ESP tuyệt đối không arm.

## ESP32

- Thư mục `FC_can_bang` là firmware; cần thêm GPS và chỉnh nguyên lý mode bay cho hợp với mô tả trên (chỉ nguyên lý mode bay).
- GPS: RX/TX cắm chân 16, 17; có cả I2C; 38400 bps; NMEA 0183 v4.0 và 4.1 hoặc UBX tùy giao thức được chọn.

## Quyết định bổ sung trong phiên

- Gửi OTP bằng Gmail App Password do chủ dự án tự điền vào file `.env`.
- Tailscale Funnel `/` chuyển từ 9Router sang web dự án.
- Nguồn firmware: GitHub Releases.
- Không nạp ESP32 lần này; chỉ build và test trên máy.
