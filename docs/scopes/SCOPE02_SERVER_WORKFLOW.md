# SCOPE-02 — PC Workflow/API mô phỏng

## 1. Mục tiêu và bàn giao

Simulated flight request, bổ sung, approve/reject, audit và Pi-facing read/status API.

## 2. Bối cảnh/trạng thái

`SCOPE-01 PASS` là điều kiện; quy trình không có giá trị pháp lý.

## 3. In scope / out of scope

In: state machine, PII tối thiểu, history, API. Out: cơ quan thật, giấy phép thật, actuator command.

## 4. Dependencies và prerequisites

SCOPE-01; owner phê duyệt simulated policy và retention.

## 5. Quyết định áp dụng

ADR-003, ADR-005, ADR-008; contracts tại `../09_API_CONTRACTS.md`.

## 6. Files

Chỉ sửa workflow/API/contracts/tests của scope; không sửa firmware/Pi.

## 7. Tasks

State machine + idempotency → object auth → history/audit → fake Pi client → offline/error behavior → tests.

## 8. API/data contracts và lỗi

409 transition conflict, 422 invalid request, 403 object policy; output bắt buộc `SIMULATED / NOT A FLIGHT PERMIT`.

## 9. Quyền, secrets, privacy, safety

Không lưu PII thừa; audit redacted; schema không có ARM/DISARM.

## 10. Test plan

Transition matrix, duplicate key, unauthorized object, stale sync, provider/server unavailable; fake clients only.

## 11. Acceptance criteria

Transitions deterministic; duplicate request safe; every mutation auditable; no actuator field/path.

## 12. Evidence

Fixtures, contract diff, test output, redacted audit samples.

## 13. Rollback/failure handling

Disable route/adapter and restore DB snapshot; preserve audit/evidence.

## 14. Definition of Done / gate

Reports complete and owner approves before SCOPE-03/04.
