# SCOPE-02 Policy Amendment — Decisions and deviations

**Status:** `IMPLEMENTED_PENDING_OWNER_ACCEPTANCE`
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)

## Ma trận capability hiện hành

| Actor | Object/action | Capability | Kết quả |
|---|---|---|---|
| `OWNER/ACTIVE` + authenticated MFA session | Create/revoke grant cho một `ADMIN/ACTIVE` khác | Owner authority | Cho phép; `If-Match`/idempotency/audit/history. |
| `ADMIN/ACTIVE`, không grant | Activate pending ordinary PC `GUEST` | `ACCOUNT_APPROVE` | Từ chối `CAPABILITY_REQUIRED`. |
| `ADMIN/ACTIVE`, có grant còn hiệu lực | `PENDING/GUEST → ACTIVE`, email verified + TOTP ready | `ACCOUNT_APPROVE` + `PC_GUEST` | Cho phép. |
| `ADMIN/ACTIVE`, grant bị revoke | Bất kỳ mutation delegated | Không còn effective capability | Từ chối ngay, không dùng cache. |
| `ADMIN/ACTIVE`, có grant | Active `GUEST → ADMIN` | `ADMIN_ROLE_APPROVE` + `PC_GUEST` | Cho phép khi request hợp lệ, không self-review. |
| `ADMIN/ACTIVE`, có grant | Reject role, review Admin/Owner, cấp/revoke grant, delegate | Ngoài scope grant | Từ chối. |
| `OWNER` target/self-review/Owner elevation | Bất kỳ delegated action | Không có capability cho Owner | Từ chối; không có path cấp `OWNER`. |
| `PENDING/SUSPENDED/REJECTED` | Reviewer action | Ineligible principal | Từ chối bất kể role/grant. |
| Pi `USER/ADMIN` | PC reviewer action | Identity domain độc lập | Không suy diễn hoặc liên thông. |

## Decisions

| ID | Quyết định | Ghi chú |
|---|---|---|
| AMD-D01 | “PC user” được map vào `PC.GUEST` active/current source role, không phải `Pi.USER`. | Không thêm role PC `USER` mới, tránh breaking schema. |
| AMD-D02 | Grant có concrete grantor/grantee, actions và `PC_GUEST` scope; không wildcard/delegation. | Tối thiểu cần cho owner policy. |
| AMD-D03 | Không tự đặt expiry duration; revoke là explicit và immediate. | Owner chưa chốt số ngày; `revoked_at` được audit. |
| AMD-D04 | Admin account approval chỉ activation sau email/MFA ready. | Không bypass onboarding/security state. |
| AMD-D05 | Admin được cấp role review chỉ approve `GUEST → ADMIN`; không reject/suspend/approve Owner. | Phạm vi đúng câu owner, least privilege. |
| AMD-D06 | UI lấy effective capability từ backend nhưng backend vẫn authorization boundary. | Stale UI chỉ gây lỗi safe `403`, không grant quyền. |

## Deviations / unresolved

- Historical SCOPE-02 D02-01 `OWNER_ONLY_REVIEW` không bị xóa; addendum này supersedes only the amended behavior and remains pending owner acceptance.
- No grant expiry, retention duration, legal hold period or deletion policy was invented.
- `Pi.USER/ADMIN` and SCOPE-02 fake Pi header remain unrelated to PC grant authorization.
- SCOPE-03 remains design/mock only. No live Pi facts or network changes were performed.
