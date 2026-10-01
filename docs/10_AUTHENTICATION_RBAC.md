# SCOPE-00 — Authentication và RBAC

## Identity domains

PC và Pi không dùng chung account/role trong prototype. PC role: `Guest` (public read), `Pending` (chờ duyệt), `Operator` (workflow mô phỏng theo policy), `Admin`, `Owner`. Pi role: `USER` và `ADMIN`; mọi account mới là `USER`. `Owner` bootstrap một lần, không có password/TOTP mặc định.

## Authentication lifecycle

1. Register → email verification → password hash → TOTP enrollment → recovery codes displayed once → pending approval.
2. Login tạo staged session; cần password, terms acceptance, email OTP và TOTP theo policy.
3. Mất Internet/email provider: trạng thái `AUTH_UNAVAILABLE`, không bypass âm thầm; session hết hạn/re-authentication vẫn bị chặn nếu thiếu factor.
4. Recovery code one-time, lưu hash, rotate toàn bộ sau recovery; đổi TOTP/password revoke session.

## Authorization matrix

| Action | Guest | Pending | Operator | Admin | Owner |
|---|---:|---:|---:|---:|---:|
| Public map | R | R | R | R | R |
| Internal map read | - | - | policy | yes | yes |
| Internal map mutate | - | - | -/explicit | yes | yes |
| Approve account/role | - | - | - | policy | yes |
| Simulated workflow | - | request only | yes | yes | yes |
| Security/bootstrap | - | - | - | limited | yes |

Backend object-level checks are authoritative. `403` and `404` behavior must avoid object enumeration. Operator is not an owner and cannot create authority claims.

## Controls

Argon2id via maintained library and measured parameters; secure cookie flags; CSRF for cookie-authenticated mutation; login/OTP/TOTP rate limit; uniform auth errors; session rotation; audit actor/action/outcome/request id without secrets. Baseline sources: OWASP ASVS/Authentication/Password Storage linked in [02_RESEARCH_REPORT.md](02_RESEARCH_REPORT.md).

## Pi rule

Pi ADMIN can manage Pi-local users, cache and research firmware area only. Pi ADMIN cannot become PC Owner or grant legal flight permission. Any future federation requires a new ADR and threat model.

## SCOPE-02 policy resolution (pre-amendment baseline)

The account and role statements in this subsection are the pre-amendment baseline. The capability-grant rules in the following subsection supersede only the affected review permissions; they do not create a PC `USER` role or change the independent Pi identity domain.

Account review uses least privilege: active `OWNER` may approve/reject/suspend another account; active `ADMIN` may list and inspect account records but cannot change status; `OPERATOR` and all non-active accounts cannot review accounts. A requester cannot review itself. `PENDING` remains blocked from internal map and workflow access even when the stored role is `OWNER` for the one-time bootstrap record. Suspension/rejection revokes all current sessions and the session guard rechecks account status on every authenticated request.

Role elevation may target only `OPERATOR` or `ADMIN`. The requester sees only its own request; the amendment below adds a narrow Owner-granted Admin review capability. There is no normal path to `OWNER`, and Pi identity/roles cannot affect PC roles.

Active `GUEST`, `OPERATOR`, `ADMIN` and `OWNER` accounts may use the simulated workflow according to object policy; `OPERATOR`, `ADMIN` and `OWNER` may review requests, while the submitter cannot decide its own request. All results are explicitly simulated and non-authoritative.

## SCOPE-02 policy amendment

`OWNER` may delegate two narrow capabilities to one specific active PC `ADMIN`: `ACCOUNT_APPROVE` and `ADMIN_ROLE_APPROVE`, both scoped to `PC_GUEST`. The grant is audited, versioned and immediately revocable; there is no wildcard, expiry assumption or further delegation. An Admin without an active grant is denied by the backend even if the UI is stale.

The delegated Admin account capability can only activate a pending ordinary PC `GUEST`; it cannot reject/suspend accounts or review Admin/Owner. The delegated role capability can only approve an active PC `GUEST` elevation request to `ADMIN`; it cannot reject, review itself, grant Owner or manage grants. This does not change the independent Pi `USER`/`ADMIN` identity domain. The existing CLI bootstrap Owner guard remains unchanged: local confirmation, password and current TOTP, no HTTP self-activation.
