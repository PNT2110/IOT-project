# SCOPE-00 — Báo cáo nghiên cứu

**Ngày truy cập nguồn:** 2026-09-22. Kết luận chỉ áp dụng trong phạm vi nguyên mẫu; vấn đề pháp lý cần review chuyên môn trước khi public.

## Pháp lý và dữ liệu vùng bay

- [Nghị định 288/2025/NĐ-CP](https://vanban.chinhphu.vn/?classid=1&docid=215810&pageid=27160&typegroupid=4), Chính phủ, ban hành và có hiệu lực 2025-11-05, là nguồn pháp lý cần lập baseline hiện hành. Cần đọc toàn văn và quy định chuyển tiếp trước khi triển khai quy trình thật.
- [Bộ Quốc phòng công bố khu vực cấm bay, hạn chế bay](https://mod.gov.vn/home/detail/%21ut/p/z1/1VJLU8IwEP4tHjjuJLE8yrGAVB1lREFoLs6SlDZCkxbSqv_etHhRB9GjmUmy-2W_zb4IJ0vCNVYqQauMxq3TI959GgeTe3_AAhp2Jj6dzoZj1mPUCweULD4b0KubIZ2OwllnMrpjNOwR_hs-PbICeor_SDjhQtvcpiTKjGzRPYK7Ya9s3CjW7jcfAhQ56hZdGShKIyBPjU5A1IeDNmkJVSlAYAYrfIMUNYg0bmS7izVIhU5xIIKu6dIoqNy2WDZGm8adTkqHbVE592UNWOW4h3cUdbS5UJJEfezQrkAfvP75GtroS-hT6QOTDIXHPOnH66_V_Z4-_7l4i_q_E_055SNyMfSOxjDukkWl4hcy12aXuYl5-GOKl5RcE55szeowbuq5KHjgemq0jV8tWf6DpubZfJ75ntPWtxdem0fB2dk7V4F_JA%21%21/dz/d5/L2dJQSEvUUt3QS80TmxFL1o2X0ZBTlI4QjFBMEc1TjgwUVRDRjE3MTAzR0Iw/), Bộ Quốc phòng, bài công bố 2025-05-30, nói cơ sở dữ liệu được quản lý theo pháp luật bảo vệ bí mật nhà nước và cập nhật theo chu kỳ/biến động. Vì vậy không tự scrape, sao chép hoặc tái phân phối dữ liệu nếu chưa kiểm tra quyền sử dụng và điều khoản nguồn.
- Không tìm thấy bằng chứng được phép để gọi một API nhà nước trong scope này. Thiết kế adapter nguồn dữ liệu có provenance, license, effective date và manual approval.

## Raspberry Pi/network

[Raspberry Pi wireless access point documentation](https://www.raspberrypi.com/documentation/configuration/wireless/wireless-access-point.md), Raspberry Pi Ltd., tài liệu hiện hành được truy cập 2026-09-22, ghi Raspberry Pi OS Bookworm dùng NetworkManager mặc định và mô tả AP trên một interface cùng upstream trên interface khác. Tài liệu cũng cảnh báo khả năng 5 GHz phụ thuộc adapter/board. Đây là cơ sở chọn NetworkManager/nmcli nhưng chipset thật vẫn phải xác minh.

AP được xem là mạng cục bộ riêng; mặc định không bridge LAN vào AP. DHCP/DNS captive portal là best-effort; URL thủ công `http://192.168.4.1` chỉ là đề xuất, phải kiểm tra xung đột subnet. mDNS có thể là convenience, không phải dependency.

## Web security và identity

- [OWASP ASVS 5.0](https://owasp.org/projects/asvs), OWASP, bản stable 5.0.0; dùng làm checklist, không phải chứng nhận.
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) và [Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), truy cập 2026-09-22: hướng dẫn password hashing chậm như Argon2id, recovery và kiểm soát authentication.
- Kết luận: password Argon2id, TOTP, email OTP TTL ngắn, recovery code hash/one-time, session rotation, CSRF, rate limit, audit và backend authorization là baseline; tham số thực tế phải benchmark ở SCOPE-01, không lấy con số từ tài liệu này.

## Geospatial

[RFC 7946 GeoJSON](https://www.rfc-editor.org/rfc/rfc7946), IETF, 2016, yêu cầu WGS 84 và thứ tự tọa độ GeoJSON là longitude, latitude. [PostGIS manual](https://postgis.net/docs/postgis-en.html) và [PostGIS geography workshop](https://postgis.net/workshops/postgis-intro/geography.html) xác nhận SRID 4326/geography phù hợp phép đo theo mét. Prototype local có thể dùng GeoJSON + Shapely; production/multi-user là decision gate sang PostGIS.

## ESP32/GNSS

- [ESP-IDF UART API](https://docs.espressif.com/projects/esp-idf/en/v5.3.4/esp32/api-reference/peripherals/uart.html) mô tả driver UART và buffer; [GPIO guide](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/gpio.html) mô tả GPIO matrix/restrictions. Đây là nguồn nền, không xác nhận board cụ thể trong archive.
- [u-blox M9 interface description](https://content.u-blox.com/sites/default/files/u-blox-M9-SPG-4.04_InterfaceDescription_UBX-21022436.pdf) mô tả NMEA/UBX cho dòng M9; [u-blox protocol specification](https://content.u-blox.com/sites/default/files/products/documents/u-blox7-V14_ReceiverDescriptionProtocolSpec_%28GPS.G7-SW-12001%29_Public.pdf) mô tả cấu trúc frame. Model module chưa được nhận diện nên không được dùng làm bằng chứng tương thích.
- Archive cho thấy `HardwareSerial(2)` với `Serial_sbus.begin(100000, SERIAL_8E2, 35, -1, true)` và code điều khiển IMU/SBUS/ESC; không có parser GNSS, NMEA, UBX, I²C hay telemetry output trong 7 file archive. Chi tiết tại [13_ESP32_FIRMWARE_AUDIT.md](13_ESP32_FIRMWARE_AUDIT.md).

## Hạn chế nghiên cứu

Không SSH Pi, không mở/đo thiết bị, không cài dependency, không benchmark, không gọi API nhà nước thật, không kiểm thử camera/USB Wi-Fi/GNSS, không flash và không điều khiển động cơ. Những điểm đó là `UNVERIFIED` hoặc `BLOCKED`, không phải PASS.
