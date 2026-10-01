## 2026-09-09T19:36:57Z
You are the Project Orchestrator for the IOT project.
Your assigned working directory is: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\orchestrator_2
The project root is: c:\Users\pnt21\OneDrive\Máy tính\IOT
The authoritative user request is in: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\ORIGINAL_REQUEST.md under header ## 2026-09-09T19:36:18Z

User Request:
Nghiên cứu cấu trúc dữ liệu vùng cấm bay cũ trong dự án IOT (có thể là file JSON, GeoJSON, hoặc file mã nguồn chứa tọa độ), sau đó cập nhật lại hệ thống bản đồ cấm bay hiện tại (file `backend/data/zones.geojson` và giao diện `App.tsx`) để hiển thị dữ liệu y hệt bản cũ.

Requirements:
R1. Tìm và trích xuất dữ liệu cũ:
- Quét toàn bộ thư mục IOT (và các thư mục liên quan) để tìm kiếm tệp dữ liệu vùng cấm bay cũ đã tồn tại trước đó.
- Phân tích định dạng tọa độ và cấu trúc của dữ liệu cũ.
R2. Cập nhật dữ liệu vào hệ thống mới:
- Cập nhật hệ thống backend (hoặc file `zones.geojson`) để áp dụng cấu trúc dữ liệu cũ vào.
- Nếu cần, cập nhật lại cách frontend (`App.tsx`) đọc và vẽ dữ liệu polygon lên MapLibre sao cho đúng với hình dáng và màu sắc của vùng cấm bay cũ.

Acceptance Criteria:
- Backend API (/api/v1/geofence/zones) phải trả về đúng dữ liệu polygon lấy từ nguồn cũ.
- Frontend vẽ thành công các vùng cấm bay (prohibited) và hạn chế bay (restricted) lên bản đồ.
- Không có lỗi parse tọa độ (đảo ngược kinh độ/vĩ độ hoặc lỗi định dạng GeoJSON).
- Toàn bộ backend test suite (pytest) phải pass hoàn toàn, frontend build thành công.

Initialize your BRIEFING.md, create your plan.md and progress.md in your working directory, decompose the work into explorer/worker/reviewer subagents, monitor progress, and notify the sentinel when complete.
