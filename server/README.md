# Máy chủ PC

FastAPI + SQLAlchemy + SQLite (`server/data/app.db`), migration bằng Alembic.

## Cấu trúc

| File | Nội dung |
|---|---|
| `app/main.py` | Tạo app, header bảo mật, giới hạn kích thước request |
| `app/api.py` | Gộp các router dưới `/api/v1` |
| `app/routers/auth.py` | Đăng ký, đăng nhập, OTP mail, 2FA, hồ sơ |
| `app/routers/zones.py` | Vùng công khai và CRUD vùng |
| `app/routers/accounts.py` | Duyệt tài khoản, đổi cấp |
| `app/routers/flights.py` | Danh sách và quyết định yêu cầu bay |
| `app/routers/device.py` | Kênh thiết bị cho Pi (đơn bay mã hóa) |
| `app/routers/deps.py` | Phiên, CSRF, kiểm tra quyền, giới hạn tần suất |
| `app/device_crypto.py` | Phong bì AES-256-GCM của kênh thiết bị |
| `cli.py` | `seed-default-owner`, `add-device`, `bootstrap-owner` |

## Quyền

| Vai trò | Ý nghĩa | Được làm |
|---|---|---|
| `OWNER` | Tài khoản chính | Mọi thứ |
| `ADMIN` | Cấp 1 | Sửa vùng, duyệt bay, duyệt tài khoản, đổi cấp |
| `OPERATOR` | Cấp 2 | Sửa vùng, duyệt bay |
| `GUEST` | Mới đăng ký | Chờ duyệt |

Khách chưa đăng nhập chỉ gọi được `GET /api/v1/public/zones` và `GET /api/v1/health`.

## Đăng nhập và đăng ký

- Đăng nhập: tài khoản (tên hoặc email) + mật khẩu + tích điều khoản → OTP mail → 2FA.
- Đăng ký: tên tài khoản, email, mật khẩu hai lần → mã mail → hiện khóa 2FA để lưu → chờ duyệt.
- Tài khoản chính mặc định (`seed-default-owner`): không có email nên bỏ qua OTP mail, 2FA lấy từ `DEFAULT_OWNER_TOTP_SECRET`.
- Bỏ dở ở bước lưu khóa 2FA: đăng nhập lại bằng mật khẩu + OTP mail sẽ được cấp khóa mới.

## Chạy

Dùng `ops/pc/start-server.ps1` (xem README gốc). Biến môi trường: `server/.env.example`.
Ở `APP_ENV=development` thư OTP không gửi đi mà ghi vào `FAKE_MAIL_OUTBOX`.

## Kiểm thử

`tests/scope01` (đăng nhập, vùng), `tests/scope02` (tài khoản, duyệt bay, CLI),
`tests/scope06` (kênh thiết bị).
