# SCOPE-04 — Pi Web

## 1. Mục tiêu và bàn giao

Pi-local auth, camera adapter, map cache, mock telemetry, 3D view.

## 2. Bối cảnh/trạng thái

Camera/model/device permissions chưa xác minh; telemetry source chưa có contract triển khai.

## 3. In scope / out of scope

In: local UI/read-only adapters/cache. Out: ARM/DISARM, real approval, firmware flash.

## 4. Dependencies và prerequisites

SCOPE-02/03 PASS, camera inventory, Pi identity policy.

## 5. Quyết định áp dụng

ADR-005, ADR-007, ADR-008; offline behavior tại `../05_SYSTEM_ARCHITECTURE.md`.

## 6. Files

Chỉ sửa Pi web/cache/camera/telemetry mock files được duyệt.

## 7. Tasks

Pi identity → fake email/MFA → camera adapter → cache provenance/stale → telemetry contract → 3D verified fields → resource tests.

## 8. API/data contracts và lỗi

Unknown telemetry → `UNAVAILABLE`; stale cache visibly labeled; camera unavailable is a typed error.

## 9. Quyền, secrets, privacy, safety

Pi ADMIN cannot become PC Owner; local stream authenticated; no command endpoint.

## 10. Test plan

Mock camera, upstream down, stale map, no-fix telemetry, role/CSRF/rate-limit tests.

## 11. Acceptance criteria

Local web/camera/cache work with upstream down; no invented field; no actuator route.

## 12. Evidence

Screenshots/logs with no PII/secret, mock fixture hashes, resource measurements.

## 13. Rollback/failure handling

Disable optional camera/3D adapter; retain local web and prior cache.

## 14. Definition of Done / gate

Reports complete; owner approves before SCOPE-06.
