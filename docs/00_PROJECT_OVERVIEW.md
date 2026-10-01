# SCOPE-00 — Tổng quan dự án

**Trạng thái:** `RESEARCH_COMPLETE_PENDING_APPROVAL`  
**Ngày:** 2026-09-22  
**Phạm vi:** nghiên cứu và kiến trúc nguyên mẫu độc lập PC ↔ Raspberry Pi 5 ↔ ESP32/GNSS.

## Kết luận điều hành

Hệ thống được thiết kế thành ba miền tin cậy độc lập:

1. PC là nơi lưu trữ chính, chạy web/API dữ liệu vùng bay và quy trình hồ sơ **mô phỏng**.
2. Pi 5 là edge station offline-first: onboard Wi-Fi phát AP liên tục, USB Wi-Fi là STA ra mạng ngoài, web cục bộ phục vụ cấu hình/giám sát.
3. ESP32 hiện chỉ là nguồn dữ liệu flight-controller/GNSS để đọc telemetry sau khi được audit; không có đường server → ARM/DISARM.

Hồ sơ được “duyệt” chỉ có nghĩa `SIMULATED / NOT A FLIGHT PERMIT`. Dữ liệu do người dùng vẽ là lớp nghiên cứu, không phải dữ liệu pháp lý. Không tài liệu nào tuyên bố hệ thống là cổng của cơ quan nhà nước.

## Bằng chứng hiện có

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| Repository hiện tại | `VERIFIED_FROM_SOURCE` | `/home/pnt/IOT`, branch `main`, worktree dirty với nhiều file đã bị xóa/thay đổi trước lượt này. |
| Archive firmware | `VERIFIED_FROM_SOURCE` | `FC_can_bang.zip`, SHA-256 `95809c58d61bb20c12a9541719ad90ec4afc8dab74597a20517486174849771f`. |
| Mã firmware trong archive | `VERIFIED_FROM_SOURCE` | 7 file `.ino`; không có `platformio.ini`, `platformio` manifest hay datasheet GNSS. |
| Pi/USB Wi-Fi/webcam | `USER_REPORTED` | Chưa SSH, không quét thiết bị, không đổi mạng. |
| Model ESP32/GNSS/USB Wi-Fi/cáp | `BLOCKED` | Cần ảnh nhãn, sơ đồ dây và lệnh inventory ở scope phần cứng sau. |
| Hệ điều hành PC/Pi hiện thời | `UNVERIFIED` | Không được truy cập Pi trong SCOPE-00. |

## Các tài liệu bắt đầu từ đâu

- [Yêu cầu và ID](01_REQUIREMENTS.md)
- [Báo cáo nghiên cứu](02_RESEARCH_REPORT.md)
- [Quyết định công nghệ/ADR](03_TECHNOLOGY_DECISIONS.md)
- [Kiến trúc hệ thống](05_SYSTEM_ARCHITECTURE.md)
- [Audit firmware](13_ESP32_FIRMWARE_AUDIT.md)
- [Roadmap](15_MASTER_ROADMAP.md)
- [Prompt SCOPE-01](CODEX_SCOPE01_PROMPT.md)

## Điểm dừng

SCOPE-00 không triển khai mã, không khôi phục file đã xóa, không SSH/flash/kết nối phần cứng, không công khai server và không xử lý giấy phép bay thật. Chờ chủ dự án phê duyệt bộ tài liệu này trước khi chạy SCOPE-01.
