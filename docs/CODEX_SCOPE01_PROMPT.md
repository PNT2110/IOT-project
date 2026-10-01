# Prompt giao việc tương lai — SCOPE-01 PC Server Foundation

Bạn là Codex triển khai **chỉ SCOPE-01** cho repository này.

## Khóa bắt buộc

**Không bắt đầu nếu chủ dự án chưa chấp thuận SCOPE-00 hoặc nếu preconditions chưa đạt.** Nếu thiếu precondition, không đoán và không viết code để “lấp chỗ trống”; tạo báo cáo `BLOCKED`.

## Đọc trước

Đọc `docs/00_PROJECT_OVERVIEW.md`, `01_REQUIREMENTS.md`, `03_TECHNOLOGY_DECISIONS.md`, `05_SYSTEM_ARCHITECTURE.md`, `08_DATABASE_DESIGN.md`, `09_API_CONTRACTS.md`, `10_AUTHENTICATION_RBAC.md`, `11_SECURITY_ARCHITECTURE.md`, `15_MASTER_ROADMAP.md`, `CODEX_IMPLEMENTATION_RULES.md` và `scopes/SCOPE01_SERVER_FOUNDATION.md`.

## Phạm vi

Chạy **local only** trên PC: nền FastAPI/React hoặc stack đã được chủ dự án chốt sau khi xác minh runtime; schema/migration tối thiểu; auth/RBAC cơ bản; dữ liệu bản đồ mô phỏng có provenance; public/internal filtering; API version/error envelope; audit mutation; test unit/contract/integration; docs và rollback.

## Ngoài phạm vi

Không public server, không SSH/Pi, không firmware/GNSS/hardware, không email provider thật, không dữ liệu pháp lý thật, không workflow phê duyệt thật, không camera/telemetry integration, không ARM/DISARM.

## Acceptance và bàn giao

Tạo test tái chạy được với fake email và fixtures. Chứng minh Guest không đọc internal zone; role checks ở backend; secrets không vào log; simulated request không có actuator field; migration/rollback hoạt động. Tạo ba report theo rules và dừng chờ duyệt SCOPE-02.
