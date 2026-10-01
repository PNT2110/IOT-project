# SCOPE-02 — Decisions, conflicts và deviations

**Status:** `IMPLEMENTED_LOCAL_ONLY`
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)

## Quyết định nghiệp vụ đã áp dụng

| ID | Quyết định | Lý do / ảnh hưởng |
|---|---|---|
| D02-01 | `OWNER` là reviewer duy nhất có quyền thay đổi trạng thái tài khoản và duyệt role elevation; `ADMIN` chỉ list/detail account; `OPERATOR` không review account. | Least privilege, tránh mơ hồ “Admin duyệt Admin”; không có self-review. |
| D02-02 | Trạng thái tài khoản: `PENDING`, `ACTIVE`, `REJECTED`, `SUSPENDED`; `REJECTED` terminal trong scope này. | Tách rõ account status với role; suspend/reject revoke toàn bộ session. |
| D02-03 | Role elevation chỉ cho `OPERATOR`/`ADMIN`, không bao giờ cho `OWNER`; duplicate request mở bị từ chối. | Không tạo đường privilege escalation ngoài policy đã xác nhận. |
| D02-04 | Hồ sơ tối thiểu chỉ gồm summary, planned start/end có timezone và polygon GeoJSON giả lập. | Giảm PII; không yêu cầu mã giấy phép, phương tiện thật hoặc GNSS. |
| D02-05 | Không implement cancel/expire. | SCOPE-00/SCOPE-02 chưa chốt nghiệp vụ; tránh tự sáng tạo transition. |
| D02-06 | Workflow reviewers là active `OPERATOR`, `ADMIN`, `OWNER`; submitter không được tự quyết định hồ sơ của mình. | Đủ workflow mô phỏng nhưng không biến role thành quyền pháp lý. |
| D02-07 | Fake Pi dùng authenticated active PC session + header test identity `X-Fake-Pi-Client: scope02-test-client`; `offline=true` trả `UNSYNCED`/`stale`. | Mock read-only, không tạo certificate/secret hay kết nối Pi thật. |
| D02-08 | Bootstrap Owner không self-activate qua HTTP; thêm CLI local-only có exact confirmation, password và TOTP hiện tại, audit actor local `null`. | Giải quyết operational gate mà không mở endpoint tự duyệt; cần owner nghiệm thu quy trình vận hành. |

## Deviations / giới hạn được ghi nhận

| ID | Deviation | Trạng thái |
|---|---|---|
| DEV02-01 | `User` trước đây chưa có version; migration SCOPE-02 thêm `users.version` để `If-Match` có nghĩa và tương thích dữ liệu cũ với default `1`. | PASS — migration/restore DB tạm |
| DEV02-02 | Idempotency replay trả cùng payload dữ liệu nhưng có thể giữ HTTP status `201` của route create. | PASS — documented safe replay; không tạo bản ghi mới |
| DEV02-03 | Audit/history reason là text nghiệp vụ đã giới hạn 500 ký tự; không lưu request body/secret. | PASS — redaction tests |
| DEV02-04 | Pi adapter là fake local contract, không chứng minh TLS/mTLS, Pi reachability hay hardware behavior. | DEFERRED_BY_SCOPE — SCOPE-03/04/06 |
| DEV02-05 | Browser harness hiện có kiểm chứng auth/pending/secure-cookie và build; UI SCOPE-02 dùng các nút tối giản, chưa có UX đầy đủ cho mọi transition/lỗi. | PASS cho local acceptance; mở rộng UX là backlog |
| DEV02-06 | Worktree vẫn dirty/untracked theo SCOPE-01; không commit/push/cleanup hoặc ghi đè ngoài manifest. | PASS — preserved |

## Câu hỏi còn cần owner nghiệm thu

1. Có chấp nhận policy `OWNER_ONLY_REVIEW` cho account status và role elevation không? Lựa chọn: **A — giữ nguyên least privilege (khuyến nghị)**; **B — cho ADMIN duyệt một tập role/status cụ thể trong scope sau**.
2. Có chấp nhận quy trình CLI bootstrap Owner yêu cầu password + TOTP + exact confirmation, không có HTTP self-activation không? Lựa chọn: **A — chấp nhận local-only (khuyến nghị)**; **B — cung cấp quy trình vận hành khác trước khi mở scope sau**.
3. Có cần retention/deletion policy cho history trước khi tích hợp Pi/public không? Lựa chọn: **A — chốt ở scope tích hợp/deployment**; **B — cung cấp thời hạn và legal hold ngay bây giờ**.

## Addendum — policy amendment 2026-09-22

The owner decision in the continuation prompt supersedes D02-01 for the amendment without deleting the historical decision:

| ID | New decision | Enforcement |
|---|---|---|
| AMD02-01 | `OWNER` grants narrow capabilities to one concrete active PC `ADMIN`; no Admin review by default. | `capability_grants`, backend DB lookup on every mutation, no cache. |
| AMD02-02 | `ACCOUNT_APPROVE` is limited to `PENDING` target `PC.GUEST → ACTIVE`; no Admin reject/suspend or Admin/Owner target. | Route-level scope check plus negative tests. |
| AMD02-03 | `ADMIN_ROLE_APPROVE` is limited to active `PC.GUEST → ADMIN`; no rejection, self-review, delegation or Owner grant. | Role decision scope check plus negative tests. |
| AMD02-04 | No expiry duration is invented because the owner has not specified one; revoke is explicit and immediate. | `revoked_at`, revoker, reason, version and transaction history. |
| AMD02-05 | “PC user” in this amendment maps to active `PC.GUEST`, not `Pi.USER`; identity domains remain separate. | Contract/docs and test fixture naming. |

### Amendment deviation

The existing SCOPE-02 implementation report remains historical `PASS_REPORTED`; this amendment has its own baseline, decisions, tests and final report. No SCOPE-03 live-network action is authorized by this amendment. Retention/legal hold remains a prerequisite before real PC↔Pi data/PII exchange or public deployment.
