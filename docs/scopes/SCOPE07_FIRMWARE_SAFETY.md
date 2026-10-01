# SCOPE-07 — Firmware & safety review

## 1. Mục tiêu và bàn giao

Review/đề xuất safety và test plan có phê duyệt riêng.

## 2. Bối cảnh/trạng thái

Firmware có actuator code theo archive; safety chưa được chứng nhận.

## 3. In scope / out of scope

In: review state machine/failure analysis/provenance. Out: uncontrolled motor/flight test, automatic server ARM, flight certification.

## 4. Dependencies và prerequisites

SCOPE-05/06 evidence, exact hardware, qualified reviewer, written safety authorization.

## 5. Quyết định áp dụng

Server remains status-only; firmware edit/flash is separate approved change.

## 6. Files

Review/report/test-plan files only unless explicit firmware-change approval.

## 7. Tasks

Review loop/SBUS/ESC → define bench safety → signed artifact/rollback design → failure analysis → approval record.

## 8. API/data contracts và lỗi

No actuator API; all failure states and stop conditions explicit.

## 9. Quyền, secrets, privacy, safety

Supervisor, physical isolation, power limits and emergency stop are mandatory prerequisites.

## 10. Test plan

Desk/static/synthetic first; field/motor tests require separately approved procedure and evidence.

## 11. Acceptance criteria

Signed review and controlled evidence; never claim “test successful” without observed evidence.

## 12. Evidence

Source hash, review checklist, risk sign-off, artifact provenance and rollback drill.

## 13. Rollback/failure handling

Use approved known-good artifact/procedure; stop and preserve evidence on anomaly.

## 14. Definition of Done / gate

Safety owner signs gate before any deployment decision.

## 15. Runtime implementation status (2026-10-01)

The Pi exposes an authenticated, Admin-only read endpoint at
`GET /api/pi/v1/firmware/status`. It reports whether configuration files,
the expected chip setting, `esptool`, and the explicitly configured serial
device appear to exist. File-presence checks do not validate signatures,
manifest contents, device identity, or safety approval.

The endpoint is status-only: it does not accept uploads, open a serial port,
invoke `esptool`, reset the ESP32, or write firmware. `can_flash` therefore
remains `false` even if every inventory check passes. The PC/public API has no
firmware-write path. This is intentional until the signed-manifest format,
manufacturer key, exact board identity, known-good rollback drill, physical
bench checklist, and separately reviewed flash procedure are available.

The Pi page must display missing checks and must never label a bundle
"verified" merely because a file exists. Do not test flashing with motors or
propellers connected; hardware deployment remains outside this status-only
implementation.
