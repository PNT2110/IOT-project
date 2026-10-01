# Hệ thống vùng cấm bay Drone (Server PC + Pi 5 + ESP32) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa dự án IOT hiện có về đúng yêu cầu của chủ dự án: web server công khai trên PC (bản đồ + vùng cấm bay + duyệt bay + duyệt tài khoản), web trên Pi 5 (AP + captive portal + camera + telemetry + xin phép bay), firmware ESP32 (GPS + khóa ARM theo cấp phép), rồi triển khai lên PC và Pi.

**Architecture:** Giữ nguyên 6 cụm module đã có (bên dưới), chỉ lấp các khoảng trống. Kênh mới duy nhất giữa các cụm là "kênh thiết bị" Pi→PC: đơn xin bay được mã hóa AES‑256‑GCM bằng khóa riêng của từng Pi, PC duyệt, Pi hỏi kết quả rồi gửi `$AUTH,ALLOW/DENY` xuống ESP. Pi không bao giờ có lệnh ARM/quay motor; ESP mặc định khóa ARM.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + SQLite, React/Vite + Leaflet (+ leaflet‑geoman), Pi: FastAPI + NetworkManager (nmcli) + v4l2‑ctl + esptool, ESP32 Arduino core 2.0.17, Tailscale Funnel.

**Spec:** yêu cầu của chủ dự án trong phiên này; bước đầu tiên khi thực thi là chép nguyên văn vào `docs/superpowers/specs/2026-10-01-drone-zone-system.md` và chép plan này vào `docs/superpowers/plans/2026-10-01-drone-zone-system.md`.

## Context — hiện trạng so với yêu cầu

Dự án **chưa đúng yêu cầu**. Đã kiểm tra code (không chỉ đọc báo cáo cũ):

| Cụm | Thư mục | Đã có | Thiếu / sai |
|---|---|---|---|
| M1 PC API | `server/app` | auth OTP+TOTP, vùng cấm CRUD, duyệt bay, duyệt tài khoản, 69 test | đăng nhập bằng email chứ không phải tài khoản; tài khoản chính không có 2FA mặc định; 4 vai trò + grant thay vì 2 cấp; **không có API nhận đơn từ Pi / trả kết quả**; phải có "zone source" mới lưu được vùng; kẹt tài khoản nếu thoát giữa bước 2FA |
| M2 PC Web | `frontend/src` | bản đồ công khai, vẽ vùng bằng click, 5 tab | không kéo sửa đỉnh; tab duyệt bay không hiện họ tên/bằng lái/GPS; tab duyệt tài khoản không có nút từ chối/chọn cấp |
| M3 Pi Web | `edge/pi5/pi5/web` | auth đủ luồng, vai trò user/admin, 66 test | UI là 1 chuỗi HTML trong `app.py`; camera chỉ chụp 1 khung; map không có nền; telemetry không tự cập nhật, pin/nhiệt độ/RC/PID không hiển thị; không chỉnh PID/độ cao; FW chỉ có trang trạng thái; đơn bay chỉ lưu RAM; cookie Secure làm hỏng đăng nhập qua HTTP; sai tên biến môi trường ESP |
| M4 Pi Network | `edge/pi5/pi5/network`, `ops/pi5` | chỉ có mock | **chưa có AP, captive portal, màn hình kết nối Wi‑Fi** |
| M5 Pi↔ESP | `edge/pi5/pi5/telemetry` | parser frame, builder lệnh, bridge cấp phép (có test) | chưa được nối vào web; cổng serial mở chỉ‑đọc |
| M6 Firmware | `firmware/FC_can_bang` | GPS NMEA 38400 chân 16/17, telemetry JSON, lệnh `$AUTH/$PID/$MAXALT/$PING`, khóa ARM mặc định | cấp phép không hết hạn khi mất Pi; PID/độ cao không lưu; GPS auto‑swap kéo TX vào chân có thể là ngõ ra GPS; giới hạn độ cao chỉ là trần ga; không có test host |
| Triển khai | `ops/` | launcher Windows, `deploy-pi.ps1` | Funnel đang trỏ vào 9Router; PC không chạy API; Pi chưa có service; PC chưa có SSH key vào Pi |

Quyết định của chủ dự án trong phiên này: SMTP = Gmail App Password (tự điền vào `.env`); Funnel `/` thay 9Router bằng web dự án; nguồn FW = GitHub Releases; **không nạp ESP lần này** (chỉ build + test host).

## Global Constraints

- PC API chỉ nghe `127.0.0.1:8765`, web tĩnh `127.0.0.1:5173`; công khai duy nhất qua `https://desktop-ja7nurv.tail7a4c6f.ts.net` (Tailscale Funnel).
- Pi: host `100.123.225.88`, user `pitan`, mã ở `~/iot`, web nghe `0.0.0.0:80`, AP gateway `192.168.4.1/24`. Lưu chính trên PC; Pi chỉ nhận `edge/pi5`, `firmware/FC_can_bang`, `contracts`, `ops/pi5`.
- Tao **không gõ mật khẩu** SSH/sudo/SMTP: chủ dự án tự chạy 1 lệnh cài SSH key và tự điền `.env`. Không ghi mật khẩu, App Password, TOTP secret vào source hay báo cáo.
- Trang web giữ thương hiệu trong `brand-spec.md` và dòng "mô hình nghiên cứu — không phải cổng chính thức của Bộ Quốc phòng"; không dùng tên/logo thật của cơ quan nhà nước trên trang công khai.
- Firmware: core `esp32:esp32@2.0.17`, FQBN `esp32:esp32:esp32`; GPS UART1 RX=16 TX=17 38400 8N1 NMEA; **không sửa** `PID.ino`, bộ lọc IMU, trộn motor. Lần này chỉ `compile`, không `upload`.
- Không có lệnh ARM/DISARM/motor từ Pi hay PC. ESP khởi động = khóa ARM.
- Thư mục chưa phải git repo → không có bước commit; mỗi task kết thúc bằng chạy lại toàn bộ test của cụm đó.
- Chạy test: `.venv\Scripts\python.exe -m pytest -q`; frontend: `npm --prefix frontend run typecheck` và `run build`.
- Dọn dẹp cuối: xóa file tạm/test rời; **giữ** bộ test hồi quy `tests/` (là mã nguồn dự án) và báo cáo.

## Review Focus

1. Pi mất Internet / PC không tới được khi gửi đơn hoặc hỏi kết quả → đơn giữ trạng thái `PENDING_SEND`, tự gửi lại, ESP vẫn bị khóa (test ở Task 9).
2. Pi chết hoặc rút USB sau khi đã cấp phép → ESP phải tự khóa ARM lần sau trong 10 s, nhưng không cắt motor đang bay (test ở Task 12).
3. Kẻ lạ gửi lại (replay) hoặc sửa gói đơn bay đã mã hóa, hoặc lệch giờ > 300 s → PC trả 401, không tạo đơn (test ở Task 4).
4. Người dùng thoát giữa chừng bước lưu mã 2FA khi đăng ký → đăng nhập lại phải được cấp lại mã, không kẹt email (test ở Task 2).
5. ESP chưa cắm / không có GPS fix khi bấm xin phép bay → form vẫn gửi được với `gps: null`, người duyệt thấy "không có định vị" (test ở Task 9 và Task 5).

---

## Giai đoạn A — Server PC (M1 + M2)

### Task 1: Tách `server/app/api.py` thành router theo cụm
**Files:** Create `server/app/routers/{__init__,deps,auth,zones,accounts,flights,device,misc}.py`; Modify `server/app/api.py` (chỉ còn `build_router()` gộp các router); Test: toàn bộ `tests/scope01`, `tests/scope02`.
**Interfaces — Produces:** `routers.deps`: `current_session`, `require_active`, `require_map_write`, `require_reviewer`, `require_account_admin` (tên mới thay `_require_*` cũ); mỗi file `router = APIRouter()`.
- [ ] Chạy `pytest -q tests/scope01 tests/scope02` → ghi lại 69 passed làm mốc.
- [ ] Di chuyển từng nhóm route, không đổi path/hành vi; xóa code chết (`api.py:136-137`, `:690`, `:1198-1199`).
- [ ] Chạy lại → 69 passed.

### Task 2: Tài khoản đăng nhập, tài khoản chính mặc định, sửa kẹt 2FA
**Files:** Modify `server/app/models.py`, `schemas.py`, `routers/auth.py`, `server/cli.py`, `server/.env.example`; Create `server/migrations/versions/0008_username_default_owner.py`; Test `tests/scope01/test_auth_flow.py`, `tests/scope02/test_owner_cli.py`.
**Interfaces — Produces:**
- `users.username` (unique, chữ thường, regex `^[a-z0-9_.-]{3,32}$`); `RegisterRequest.username` thay cho tên hiển thị.
- `LoginRequest{identifier, password, terms_accepted, terms_version}` — `identifier` là username hoặc email. Trả `next: "EMAIL_OTP" | "TOTP"`.
- `python -m server.cli seed-default-owner` — đọc `DEFAULT_OWNER_USERNAME`, `DEFAULT_OWNER_PASSWORD`, `DEFAULT_OWNER_TOTP_SECRET` từ môi trường; tạo OWNER `ACTIVE`, `email=NULL`, TOTP đã kích hoạt; chạy lại không đổi gì. Cũng tạo sẵn 1 `ZoneSource` `OPERATOR_DRAWN` tên "Vùng do cán bộ vẽ".
- [ ] Test: `test_login_by_username`, `test_default_owner_skips_email_otp` (login → `next == "TOTP"`, không có mail nào gửi), `test_seed_default_owner_idempotent`, `test_reenroll_after_abandoned_mfa` (enroll, bỏ, login lại bằng mật khẩu + OTP mail → được `/auth/mfa/enroll` lần nữa, secret mới), `test_register_requires_username`.
- [ ] Chạy → FAIL. Cài đặt. Chạy → PASS; toàn bộ scope01/02 PASS.
- [ ] `GET /api/v1/health` trả thêm `terms_version` để frontend không hard‑code.

### Task 3: Hai cấp quyền
**Files:** Modify `routers/accounts.py`, `routers/deps.py`, `schemas.py`; Test `tests/scope02/test_account_and_roles.py`.
**Interfaces — Produces:** vai trò giữ enum cũ, ánh xạ: OWNER = tài khoản chính, **ADMIN = cấp 1** (duyệt tài khoản + nâng/hạ cấp), **OPERATOR = cấp 2** (chỉ sửa vùng + duyệt bay), GUEST = chờ duyệt.
- `POST /api/v1/account-review/users/{id}/status` body `{status: "ACTIVE"|"REJECTED"|"SUSPENDED", role?: "ADMIN"|"OPERATOR"}` — duyệt bắt buộc có `role`.
- `POST /api/v1/account-review/users/{id}/role` body `{role: "ADMIN"|"OPERATOR"}`.
- `require_account_admin`: OWNER hoặc ADMIN (bỏ điều kiện capability grant); ADMIN không sửa được OWNER hay chính mình.
- [ ] Test: `test_admin_approves_with_role_operator`, `test_operator_cannot_list_or_approve_accounts` (403), `test_operator_can_edit_zone_and_decide_flight`, `test_admin_promotes_operator_to_admin`, `test_admin_cannot_change_owner` (403), `test_approve_without_role_rejected` (422).
- [ ] Chạy → FAIL → cài đặt → PASS. Sửa các test cũ dựa trên grant cho khớp mô hình mới.

### Task 4: Kênh thiết bị Pi→PC (đơn bay mã hóa)
**Files:** Create `server/app/device_crypto.py`, `routers/device.py`, `server/migrations/versions/0009_devices_device_flights.py`, `contracts/v1/DEVICE_FLIGHT_CONTRACT.md`, `tests/scope06/test_device_channel.py`, `tests/scope06/conftest.py`; Modify `models.py`, `server/cli.py`.
**Interfaces — Produces:**
- `device_crypto.seal(key: bytes, device_id: str, payload: dict, now: int) -> dict` → `{device_id, ts, nonce, ciphertext}` (base64url; AES‑256‑GCM, nonce 12 byte, AAD = `f"{device_id}|{ts}"`).
- `device_crypto.open_sealed(key: bytes, envelope: dict, now: int, max_skew: int = 300) -> dict`; ném `DeviceAuthError`.
- Bảng `devices(id, name, key_encrypted, created_at, revoked_at)`; `python -m server.cli add-device --name pitan` in `DEVICE_ID=` và `DEVICE_KEY=` một lần.
- `POST /api/v1/device/flight-requests` (body = envelope) → 201 `{request_id, status: "PENDING"}`. Payload: `client_ref, applicant_full_name, license_code, flight_date "YYYY-MM-DD", flight_time "HH:MM", vehicle, pi_username, gps: {lat, lon, fix_state, satellites} | null`. Cùng `client_ref` → trả lại `request_id` cũ.
- `POST /api/v1/device/flight-requests/{id}/status` (body = envelope với payload `{request_id}`) → `{status: "PENDING"|"APPROVED"|"REJECTED", reason, decided_at}`. Đơn của thiết bị khác → 404.
- Đơn lưu vào `SimulatedFlightRequest` với `device_id`, `requester_id=NULL`, trạng thái `SUBMITTED`; `geometry`/`summary` cho phép NULL. `APPROVED_SIMULATED` → `APPROVED`.
- Nonce đã dùng lưu trong bộ nhớ theo `(device_id, nonce)` trong 600 s.
- [ ] Test: `test_seal_open_roundtrip`, `test_known_vector` (vector cố định ghi trong contract), `test_tampered_ciphertext_401`, `test_replayed_nonce_401`, `test_clock_skew_301s_401`, `test_revoked_device_401`, `test_submit_then_pending_then_approved`, `test_rejected_returns_reason`, `test_duplicate_client_ref_same_id`, `test_gps_null_accepted`, `test_other_device_cannot_read_404`.
- [ ] FAIL → cài đặt → PASS.

### Task 5: Giao diện web PC
**Files:** Modify `frontend/src/api.ts`, `components/auth/AuthPanel.tsx`, `components/map/MapPanel.tsx`, `components/operations/OperationsWorkspace.tsx`, `App.tsx`, `package.json` (thêm `@geoman-io/leaflet-geoman-free`); Delete `frontend/src/styles (1).css`.
- [ ] Đăng nhập: ô "Tài khoản" (username/email) + mật khẩu + tích điều khoản; bước OTP mail bị bỏ qua khi server trả `next: "TOTP"`. Đăng ký: tên tài khoản, mail, pass, nhập lại pass → mã mail → hiện mã 2FA + QR (`otpauth_uri`) + ô tích "đã lưu". Nội dung điều khoản thật thay câu placeholder; `terms_version` lấy từ `/health`.
- [ ] Bản đồ: geoman cho vẽ đa giác/chữ nhật, kéo sửa đỉnh, xóa; chọn loại Cấm bay / Hạn chế bay; không cần tạo zone source. Khách chưa đăng nhập: chỉ bản đồ + vùng, không control vẽ.
- [ ] Tab theo vai trò: OPERATOR thấy "Bản đồ & vùng", "Duyệt xin phép bay"; ADMIN/OWNER thêm "Duyệt tài khoản". Bỏ tab tự tạo đơn bay trên PC và tab xin quyền.
- [ ] Tab duyệt bay: mỗi đơn hiện họ tên, mã bằng lái, ngày, giờ, phương tiện, thiết bị, vị trí GPS trên bản đồ nhỏ (hoặc "Không có định vị"); ô lý do; nút Duyệt / Từ chối.
- [ ] Tab duyệt tài khoản: danh sách chờ với nút Duyệt (chọn Cấp 1 / Cấp 2) và Từ chối; danh sách đang hoạt động với đổi cấp, khóa.
- [ ] `npm --prefix frontend run typecheck` và `run build` → không lỗi.

### Task 6: Chạy và công khai server
**Files:** Create `ops/pc/start-server.ps1`, `ops/pc/stop-server.ps1`; Modify `server/.env.example`, `ops/pc/static-server.mjs` nếu cần; Delete `ops/pc/migrate.sh`, `ops/pc/restart.sh` (chỉ chạy được trên Linux).
- [ ] `start-server.ps1`: đọc `server/.env`, build frontend với `VITE_PUBLIC_HOST=desktop-ja7nurv.tail7a4c6f.ts.net`, `alembic upgrade head`, `seed-default-owner`, chạy uvicorn `127.0.0.1:8765` + `node ops/pc/static-server.mjs` `127.0.0.1:5173` ở nền, ghi PID vào `runtime/pc/`. Không hỏi tương tác.
- [ ] Tạo `server/.env` từ mẫu với các ô trống `SMTP_PASSWORD`, `DEFAULT_OWNER_PASSWORD`; `DEFAULT_OWNER_TOTP_SECRET` và `SESSION_SECRET` sinh ngẫu nhiên tại chỗ. **Dừng, nhờ chủ dự án điền 2 mật khẩu.**
- [ ] `python -m server.cli add-device --name pitan` → chép `DEVICE_ID/DEVICE_KEY` vào `ops/pi5/pi.env` (file không nằm trong báo cáo).
- [ ] Đổi Funnel: `tailscale funnel reset` rồi `tailscale funnel --bg 5173`. Kiểm tra `tailscale funnel status` trỏ `127.0.0.1:5173`.
- [ ] Kiểm tra: `curl https://desktop-ja7nurv.tail7a4c6f.ts.net/api/v1/health` → 200; `/api/v1/public/zones` → 200; `/api/v1/auth/me` → 401; `/docs` → 404.

## Giai đoạn B — Pi 5 (M3 + M4 + M5)

### Task 7: Truy cập Pi + mạng AP/captive portal/kết nối Wi‑Fi
**Files:** Create `edge/pi5/pi5/network/nm.py`, `edge/pi5/pi5/web/routes_network.py`, `ops/pi5/pi-network.sh`, `tests/scope03/test_network.py`; Modify `edge/pi5/pi5/network/adapters.py`.
**Interfaces — Produces:** `NmcliAdapter(run=subprocess.run, upstream_iface="wlan1", ap_iface="wlan0")` với `status() -> {upstream_connected: bool, ssid, ip}`, `scan() -> list[{ssid, signal, secure}]`, `connect(ssid: str, psk: str | None) -> {ok: bool, error}`. Route: `GET /api/pi/v1/network/status`, `GET /api/pi/v1/network/scan`, `POST /api/pi/v1/network/connect`; route dò captive `/generate_204`, `/hotspot-detect.html`, `/connecttest.txt`, `/ncsi.txt`, `/redirect` → 302 về `http://192.168.4.1/`.
- [ ] Sinh SSH key `~/.ssh/id_ed25519` trên PC; **nhờ chủ dự án tự chạy 1 lệnh** chép public key vào Pi (họ tự gõ mật khẩu Pi). Xác nhận `ssh -o BatchMode=yes pitan@100.123.225.88 true` và `sudo -n true`.
- [ ] Kiểm kê chỉ‑đọc trên Pi: `nmcli dev`, `ip route`, `iw dev`, service `f450-ap`, `/dev/video*`, `/dev/serial/by-id`. Ghi interface đang mang default route/Tailscale.
- [ ] Test (runner giả): `test_status_parses_nmcli`, `test_scan_dedupes_and_sorts_by_signal`, `test_connect_rejects_bad_ssid`, `test_connect_wrong_password_returns_error`, `test_network_routes_open_only_when_offline` (đã có upstream → `scan/connect` cần admin, 401 nếu chưa đăng nhập), `test_captive_probe_redirects`.
- [ ] FAIL → cài đặt → PASS.
- [ ] `pi-network.sh` (idempotent): từ chối chạy nếu `ap_iface` là interface đang mang default route; tạo profile NetworkManager AP `F450` trên radio onboard (`ipv4.method shared`, `192.168.4.1/24`, autoconnect, giữ mật khẩu AP hiện có), USB dongle làm STA; ghi `/etc/NetworkManager/dnsmasq-shared.d/captive.conf` với `address=/#/192.168.4.1`. Chạy trên Pi, xác nhận Tailscale còn sống sau khi áp dụng; nếu mất, service `f450-ap` cũ được khôi phục bằng timer hoàn tác 120 s.

### Task 8: Tách UI Pi, đăng nhập qua HTTP, tài khoản mặc định, màn hình theo vai trò
**Files:** Create `edge/pi5/pi5/web/ui/{index.html,app.js,views/*.js}`, `edge/pi5/pi5/web/ui/vendor/` (leaflet, three.js bản local vì máy khách AP không có Internet), `edge/pi5/pi5/web/routes_{auth,camera,map,telemetry,admin,firmware,flight}.py`; Modify `web/app.py` (chỉ còn factory + mount), `web/asgi.py`, `web/auth.py`, `pi5/cli.py`; Test `tests/scope04/test_pi_web.py`.
**Interfaces — Produces:** `PiWebConfig.secure_cookies` lấy từ `PI_COOKIE_SECURE` (mặc định `false` trên AP HTTP); `asgi.py` đọc `PI_ESP_USB_DEVICE`; `python -m pi5.cli seed-default-admin` đọc `PI_DEFAULT_ADMIN_USERNAME/PASSWORD/TOTP_SECRET`, idempotent; `GET /api/pi/v1/auth/me` dùng để khôi phục phiên khi tải lại trang.
- [ ] Test: `test_seed_default_admin_idempotent`, `test_default_admin_first_login_requires_email_then_otp` (đã có, giữ), `test_session_cookie_not_secure_when_configured`, `test_user_gets_403_on_map_telemetry_firmware_flight`, `test_index_served_from_static`.
- [ ] FAIL → cài đặt → PASS; 28 test cũ của `test_pi_web.py` vẫn PASS.
- [ ] UI: màn 1 kết nối Wi‑Fi (khi `upstream_connected == false`) → màn 2 đăng nhập/đăng ký. USER: chỉ camera + nút "Xin quyền admin" trên thanh trên. ADMIN: 5 tab Camera / Bản đồ / Thông số / Người dùng / Firmware + nút "Xin cấp phép bay" trên thanh trên. Xóa chữ "PC simulator" và nút webcam laptop.

### Task 9: Camera, bản đồ, telemetry + tinh chỉnh, người dùng, xin phép bay
**Files:** Create `edge/pi5/pi5/telemetry/esp_link.py`, `edge/pi5/pi5/web/device_crypto.py` (bản sao khớp contract), `edge/pi5/pi5/web/authority.py`; Modify `web/camera.py`, `web/flight.py`, `web/pc_sync.py`, `web/persistence.py`, các `routes_*.py`, `ui/views/*.js`; Test `tests/scope04/test_pi_features.py`, `tests/scope06/test_pi_authority.py`.
**Interfaces — Consumes:** contract Task 4; `esp_command.auth_allow/auth_deny/set_pid/set_max_altitude/ping`, `EspFlightAuthorizationBridge`, `parse_esp_frame` (đã có).
**Produces:**
- `EspLink(device: str)`: `latest() -> dict | None`, `send(line: str) -> None`, `pause()`, `resume()`; luồng nền đọc frame mới nhất và gửi `$PING` mỗi 2 s. Là chủ duy nhất của cổng serial.
- `GET /api/pi/v1/camera/stream` → `multipart/x-mixed-replace` MJPEG từ một tiến trình `v4l2-ctl --set-fmt-video=pixelformat=MJPG --stream-mmap --stream-to=-` dùng chung, cắt khung theo mốc `FFD8…FFD9`.
- `GET /api/pi/v1/map/zones` (cache từ `PI_PC_MAP_URL`), `GET /api/pi/v1/tiles/{z}/{x}/{y}.png` (proxy OSM có cache đĩa), không có route sửa.
- `POST /api/pi/v1/tuning/pid {axis: "roll"|"pitch"|"yaw"|"angle", kp, ki, kd}`, `POST /api/pi/v1/tuning/max-altitude {meters: 2..500}` — admin + CSRF; 409 nếu `arm_state == "ARMED"`.
- `GET /api/pi/v1/admin/active` (phiên có hoạt động trong 5 phút), `POST /api/pi/v1/admin/role-requests/{id} {decision: "APPROVED"|"REJECTED"}`.
- `POST /api/pi/v1/flight/requests {full_name, license_code, flight_date, flight_time, vehicle}` → lấy GPS từ `EspLink.latest()` (không có fix → `gps: null`), lưu SQLite, `AuthorityClient.submit()`; `GET /api/pi/v1/flight/requests/current`. Danh sách phương tiện từ `PI_VEHICLES` (mặc định `F450 PNT PVD`).
- `AuthorityClient(base_url, device_id, key)`: `submit(req) -> request_id`, `poll(request_id) -> status`. Vòng nền 5 s: `PENDING_SEND` → gửi lại; `PENDING` → hỏi; `APPROVED` → `bridge.apply_decision(allow, seconds = tới hết giờ bay + PI_FLIGHT_WINDOW_MIN(60) phút)` và `refresh()` mỗi 30 s; `REJECTED` → `$AUTH,DENY`. Khởi động Pi luôn gửi `$AUTH,DENY` nếu không có đơn được duyệt còn hạn.
- [ ] Test: `test_mjpeg_splitter_yields_complete_frames`, `test_stream_requires_login`, `test_zone_uses_classification_field`, `test_tuning_pid_sends_checked_line`, `test_tuning_rejected_when_armed_409`, `test_tuning_forbidden_for_user_403`, `test_active_users_excludes_idle`, `test_admin_rejects_role_request`, `test_flight_submit_without_gps_sends_null`, `test_flight_submit_pc_unreachable_stays_pending_send_and_retries`, `test_approved_sends_auth_allow`, `test_rejected_sends_auth_deny`, `test_boot_sends_deny`, `test_pi_seal_matches_server_vector`.
- [ ] FAIL → cài đặt → PASS.
- [ ] UI: camera `<img src=stream>`; bản đồ Leaflet chỉ‑xem + chấm vị trí; tab thông số cập nhật 2 Hz: độ cao baro, roll/pitch/yaw, % pin, nhiệt độ, 8 kênh RC dạng thanh, form PID + độ cao tối đa, mô hình 3D three.js xoay theo roll/pitch/yaw; form xin phép bay + trạng thái Chờ duyệt / Được phép bay / Bị từ chối.

### Task 10: Cập nhật firmware từ GitHub Releases
**Files:** Modify `edge/pi5/pi5/web/firmware.py`, `routes_firmware.py`; Create `ops/release-firmware.md` (hướng dẫn chủ dự án đăng bản phát hành); Test `tests/scope07/test_firmware_update.py`.
**Interfaces — Produces:** `PI_FW_GITHUB_REPO="owner/repo"`; `GET /api/pi/v1/firmware/latest` → `{version, asset, sha256, current_version}` (asset `FC_can_bang.bin` + `FC_can_bang.bin.sha256` trong release mới nhất); `POST /api/pi/v1/firmware/flash {version}` → 202 `{job_id}`; `GET /api/pi/v1/firmware/jobs/{id}` → `{state: "DOWNLOADING"|"VERIFYING"|"FLASHING"|"DONE"|"FAILED", detail}`. Nạp bằng `esptool --chip esp32 -p <dev> -b 460800 write_flash 0x10000 <bin>` với `EspLink.pause()`/`resume()` bao quanh.
- [ ] Test (HTTP và esptool giả): `test_latest_parses_release`, `test_repo_not_configured_503`, `test_sha_mismatch_fails_without_flashing`, `test_flash_refused_when_armed_409`, `test_flash_refused_for_user_403`, `test_flash_pauses_and_resumes_link_even_on_failure`.
- [ ] FAIL → cài đặt → PASS. Lần này **không** chạy nạp thật.

### Task 11: Triển khai lên Pi
**Files:** Modify `ops/deploy-pi.ps1`, `ops/pi5/pi-setup.sh`; Create `ops/pi5/pi.env.example`.
- [ ] `pi-setup.sh`: cài `v4l-utils`, `esptool`, `network-manager`; venv + lock (thêm `pyserial` nếu cần); ghi `~/iot/pi.env` (quyền 600) từ file PC; unit `iot-pi-web.service` chạy cổng 80 với `AmbientCapabilities=CAP_NET_BIND_SERVICE`; chạy `seed-default-admin`; `SKIP_FLASH=1` mặc định, chỉ `arduino-cli compile`.
- [ ] `deploy-pi.ps1` dùng SSH key (BatchMode), không hỏi mật khẩu. **Nhờ chủ dự án điền** `PI_SMTP_PASSWORD`, `PI_DEFAULT_ADMIN_PASSWORD` trong `ops/pi5/pi.env` trước khi chạy.
- [ ] Chạy deploy; `systemctl is-active iot-pi-web` → `active`; `curl http://192.168.4.1/health` trên Pi → 200.

## Giai đoạn C — Firmware ESP32 (M6)

### Task 12: Nguyên lý mode bay + GPS + lưu tham số
**Files:** Create `firmware/FC_can_bang/flight_gate.h` (logic thuần C++, không phụ thuộc Arduino), `tests/firmware/test_gps_nmea.cpp`, `tests/firmware/test_flight_gate.cpp`, `tests/firmware/test_host_build.py`; Modify `FC_can_bang.ino`, `MODE.ino`, `Link.ino`, `GPS.ino`, `Sbus.ino`, `contracts/v1/SCOPE05_ESP32_USB_TELEMETRY_CONTRACT.md`.
**Interfaces — Produces:**
- `struct ArmInputs { bool rc_ok, auth_allowed, link_alive, gps_ok, mode_angle, arm_switch_seen_low, arm_switch_high; int throttle_us; };`
- `const char* arm_block_reason(const ArmInputs&)` → `"READY"`, `"RC_LOST"`, `"NO_FLIGHT_AUTHORIZATION"`, `"PI_LINK_LOST"`, `"NO_GPS_FIX"`, `"MODE_NOT_ANGLE"`, `"ARM_SWITCH_NOT_RESET"`, `"THROTTLE_HIGH"`, `"ARM_SWITCH_LOW"` (thứ tự ưu tiên như liệt kê).
- `int altitude_throttle_cap(AltLimiter& s, float rel_alt_m, float max_alt_m, int throttle_us)`: vượt trần → chốt trần ga tại ga hiện tại − 30 rồi hạ 1 µs mỗi vòng (không dưới 1100) cho tới khi thấp hơn trần 1 m thì nhả.
- `link_alive` = có `$PING` trong 10 000 ms; chỉ chặn lần ARM mới, không disarm khi đang bay.
- Mode: `BLOCKED` (chưa cấp phép), `ANGLE`, `KILL`, `FAILSAFE`; telemetry `flight.mode` thêm giá trị `BLOCKED`.
- GPS: UART1 RX=16, chân TX để `-1` trong lúc dò (không kéo vào ngõ ra GPS); chỉ khóa chân sau 3 câu NMEA đúng checksum; dò lại mỗi 3 s chỉ khi chưa khóa.
- `Preferences` namespace `"fc"` lưu PID và `max_altitude_m` khi nhận `$PID`/`$MAXALT`; nạp lại lúc khởi động.
- SBUS byte 23 bit 3 (failsafe) → `sbus_status = false`.
- [ ] Test host (g++ của Strawberry tại `C:\Strawberry\c\bin`; `test_host_build.py` biên dịch + chạy, skip nếu không có g++): GGA/RMC hợp lệ, sai checksum bị loại, RMC `V` → không fix; mỗi giá trị `arm_block_reason`; `link_alive=false` → `"PI_LINK_LOST"`; hết hạn cấp phép khi đang bay không đổi trạng thái ARM; giới hạn độ cao chốt, hạ dần, nhả.
- [ ] FAIL → cài đặt → PASS.
- [ ] Build trên Pi (Task 11): `arduino-cli compile -b esp32:esp32:esp32 firmware/FC_can_bang` → thành công, ghi kích thước + SHA‑256. **Không upload.**
- [ ] Sửa `tests/scope05/test_esp_usb.py` cho giá trị `BLOCKED` và `PI_LINK_LOST`.

## Giai đoạn D — Kiểm thử tổng, báo cáo, dọn dẹp

### Task 13: Kiểm thử đầu‑cuối
- [ ] `pytest -q` toàn bộ → 0 failed; `npm --prefix frontend run typecheck && run build`; `node --test tests/ops/static-server.test.mjs`.
- [ ] Cục bộ (mail ghi ra outbox thử): đăng ký → mã mail → 2FA → chờ duyệt → tài khoản chính duyệt Cấp 2 → cấp 2 vẽ/sửa/xóa vùng, duyệt bay, bị chặn ở duyệt tài khoản; khách chỉ thấy bản đồ. Dùng trình duyệt trong app chụp bằng chứng.
- [ ] PC↔Pi thật: trên Pi đăng nhập tài khoản mặc định, gửi đơn xin bay → hiện ở tab duyệt trên web công khai → duyệt → Pi hiện "Được phép bay"; đơn thứ hai → từ chối → Pi hiện "Bị từ chối". Kiểm tra dòng lệnh `$AUTH,…` Pi ghi ra cổng serial (log), không yêu cầu ESP đã nạp bản mới.
- [ ] Pi thật: camera stream ra khung hình; bản đồ lấy vùng từ URL Funnel; điện thoại vào Wi‑Fi `F450` tự bật trang; rút dongle Wi‑Fi → màn 1 (nếu chủ dự án có mặt để thao tác; nếu không ghi "chưa kiểm").
- [ ] Mail thật: một lần đăng nhập trên web công khai sau khi chủ dự án điền App Password — chủ dự án tự đọc mã.

### Task 14: Báo cáo và dọn dẹp
- [ ] Viết `docs/reports/FINAL_DEPLOY_REPORT_2026-10-01.md`: bảng yêu cầu → trạng thái (đã kiểm thật / chỉ test tự động / chưa kiểm), kết quả lệnh test, URL công khai, cách khởi động lại PC và Pi, việc còn lại (nạp ESP, la bàn I2C của GPS, UBX, chân đo pin, tự khởi động server khi bật máy).
- [ ] Cập nhật `README.md` (đang mô tả triển khai Ubuntu cũ) và `contracts/v1/README.md`.
- [ ] Xóa: `runtime/pi-sim/`, `.pytest_cache/`, `tools/__pycache__/`, `ops/pi5/__pycache__/`, outbox OTP thử, DB thử, ảnh chụp tạm, `server/.venv` thừa, `/tmp/iot-pi.tgz` trên Pi; dừng tiến trình thử ở cổng 4173 và 8082 (xác nhận đúng là của dự án trước khi dừng). Liệt kê thư mục trước khi xóa.

## Việc cần chủ dự án làm (tao không làm thay được)

1. Chạy 1 lệnh cài SSH key vào Pi (tự gõ mật khẩu Pi) — đầu Task 7.
2. Điền `SMTP_PASSWORD` (Gmail App Password) và mật khẩu tài khoản mặc định vào `server/.env` và `ops/pi5/pi.env`.
3. Cho tên repo GitHub chứa bản phát hành firmware (`PI_FW_GITHUB_REPO`).

## Thứ tự và phụ thuộc

Task 1→2→3→4→5→6 (server) ; Task 7→8→9→10→11 (Pi; Task 9 cần contract Task 4) ; Task 12 độc lập, build ở Task 11 ; Task 13→14 cuối. Giai đoạn A và Task 12 làm được ngay; giai đoạn B chờ SSH key.
