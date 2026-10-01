# SCOPE-00 — Quyết định công nghệ và ADR

## ADR-001 — Modular monorepo, local-first

**Context:** repository hiện có dấu vết backend Python và frontend React trong `HEAD`, nhưng worktree hiện tại đang dirty/xóa nhiều file.  
**Decision:** giữ monorepo modular; SCOPE-01 chỉ tạo nền PC local. Pi và firmware là module/adapter riêng, không dùng chung secret store hay identity mặc định.  
**Alternatives:** tách repo ngay (đồng bộ contract khó hơn); monolith triển khai trực tiếp (ranh giới safety kém).  
**Trade-off/reversal:** dễ chia sẻ schema nhưng phải kỷ luật boundary; có thể tách repo sau khi contract ổn định.

## ADR-002 — FastAPI + React/TypeScript là baseline cần xác minh

**Decision:** dùng FastAPI/Uvicorn + Pydantic cho API và React/TypeScript/Vite cho UI trong SCOPE-01, vì `HEAD` có requirements/package manifest tương ứng. Không coi các version/implementation trong `HEAD` là đang chạy.  
**Alternatives:** Django; server-rendered UI.  
**Trade-off:** stack hiện có giảm migration nhưng cần kiểm tra dependency lock và license.  
**Rollback:** thay adapter HTTP/UI, giữ domain contracts.

## ADR-003 — SQLite local, PostGIS trước production

**Decision:** SCOPE-01 dùng SQLite local với schema versioned, geometry GeoJSON/validated; không gọi đó là production spatial store. Trước SCOPE-06/08 phải benchmark concurrency và quyết định PostgreSQL/PostGIS.  
**Alternatives:** PostGIS ngay (vận hành nặng cho local); document DB (kém constraint/audit).  
**Reversal:** migration script dựa trên schema contract và fixtures.

## ADR-004 — MapLibre/GeoJSON/PMTiles, không khóa vào tile provider

**Decision:** frontend map adapter trừu tượng hóa MapLibre; dữ liệu vector là GeoJSON cho prototype, PMTiles/offline cache chỉ sau khi kiểm tra license/size. Không dùng Google Maps API hoặc tile nguồn không được phép.  
**Sources:** RFC 7946 và PostGIS trong [02_RESEARCH_REPORT.md](02_RESEARCH_REPORT.md).  
**Reversal:** thay renderer không thay canonical coordinate contract.

## ADR-005 — Hai miền identity

**Decision:** PC `Owner/Admin/Operator/Pending/Guest` và Pi `USER/ADMIN` là hai policy domains độc lập ở prototype. Không suy ra email verification của miền này là của miền kia; không SSO ngầm.  
**Reason:** giảm blast radius và phù hợp edge offline.  
**Reversal:** federation chỉ sau threat model, enrollment và audit riêng.

## ADR-006 — Pi NetworkManager AP + USB STA

**Decision:** onboard AP autostart liên tục; USB adapter là STA/upstream; route/NAT không làm ảnh hưởng AP. SSID/IP/channel chỉ là config runtime và phải kiểm tra conflict. Captive portal là best-effort với URL thủ công.  
**Source:** Raspberry Pi AP documentation trong [02_RESEARCH_REPORT.md](02_RESEARCH_REPORT.md).  
**Reversal:** nếu chipset không hỗ trợ concurrent AP+STA, dùng Ethernet/second adapter hoặc đổi hardware; không ép bằng script tùy tiện.

## ADR-010 — SCOPE-03 owner override: single-radio AP + STA

The owner has superseded ADR-006's target topology for the verified Pi deployment profile: managed `wlan0` is the upstream STA and `ap0` is the local F450 AP on one onboard PHY. The old USB-STA topology remains historical evidence and is not silently rewritten. Same-PHY operation requires same-channel synchronization and must be validated on the real device. See [ADR-SCOPE03-SINGLE-RADIO-AP-STA.md](ADR/ADR-SCOPE03-SINGLE-RADIO-AP-STA.md).

**Status:** `OWNER_OVERRIDE — LIVE_VALIDATION_PENDING`; this is documentation only and does not authorize SSH, network mutation, N4, PC↔Pi exchange or later scopes.

## ADR-007 — Camera: adapter, ưu tiên MJPEG prototype; WebRTC là decision gate

**Decision:** bắt đầu bằng camera adapter read-only và mock; chọn MJPEG/HTTP nội bộ chỉ khi USB camera và CPU đo được. WebRTC chỉ sau benchmark latency/CPU/permissions.  
**Alternatives:** HLS (latency cao), WebRTC (phức tạp), raw device exposure (không an toàn).  
**Rollback:** giữ snapshot/read-only.

## ADR-008 — Telemetry WebSocket/SSE nhưng phải có polling fallback

**Decision:** API REST là canonical; WebSocket hoặc SSE chỉ là transport realtime có sequence/stale marker, polling là fallback. Không gửi command channel từ PC/Pi tới FC trong prototype.  
**Reason:** dễ replay/diagnose và không biến realtime thành safety path.

## ADR-009 — Release theo evidence gate

**Decision:** mỗi scope tạo implementation/test/final report với `PASS/FAIL/NOT_RUN/BLOCKED`, diff và rollback. Không commit/push/public deploy nếu chưa được yêu cầu.  
**Reason:** worktree dirty và phần cứng có rủi ro cao.
