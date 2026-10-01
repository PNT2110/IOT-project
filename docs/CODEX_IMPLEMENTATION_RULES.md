# Quy tắc thực thi cho Codex

1. Chỉ thực thi scope được giao; đọc `docs/` và ghi kế hoạch trước khi sửa.
2. Kiểm tra `git status`, branch và diff; không ghi đè thay đổi chưa commit; không reset/restore/clean; không commit/push nếu chưa được yêu cầu.
3. Không SSH, truy cập phần cứng, đổi mạng, flash, cập nhật firmware, công khai dịch vụ, ARM/DISARM hoặc hành động phá hủy nếu scope và phê duyệt chưa cho phép.
4. Không hard-code password, API token, recovery code, TOTP secret hoặc Wi-Fi password; không in chúng vào log.
5. Mock phải ghi rõ `MOCK`/`SIMULATED`; không biến kết quả mô phỏng thành phép đo, giấy phép hay xác nhận của cơ quan thật.
6. Backend là lớp authorization; UI không phải security boundary. Mọi mutation có audit và test.
7. Mọi thay đổi có test, acceptance evidence và rollback. Gặp blocker thì dừng scope, không tự vượt scope.
8. Dọn file test theo manifest/phân loại; không xóa source gốc, dữ liệu, bằng chứng hay file chưa rõ tác dụng.
9. Cuối mỗi scope tạo `SCOPEXX_IMPLEMENTATION_REPORT.md`, `SCOPEXX_TEST_REPORT.md`, `SCOPEXX_FINAL_REPORT.md`, liệt kê `PASS/FAIL/NOT_RUN/BLOCKED` kèm bằng chứng.
10. Các tài liệu pháp lý/dữ liệu vùng bay phải nêu nguồn, license, thời điểm cập nhật và giới hạn; không nhận là cổng nhà nước.
11. Hồ sơ luôn gắn `SIMULATED / NOT A FLIGHT PERMIT`; không tạo server-to-FC ARM/DISARM path.
