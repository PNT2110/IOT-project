# SCOPE-05 — ESP32 read-only audit và GNSS/telemetry

## 1. Mục tiêu và bàn giao

Audit source/model/wiring và passive/read-only telemetry/GNSS validation.

## 2. Bối cảnh/trạng thái

Archive evidence tại `../13_ESP32_FIRMWARE_AUDIT.md`; model/wiring `BLOCKED`.

## 3. In scope / out of scope

In: inventory, synthetic fixtures, passive/read-only capture. Out: firmware edit, persistent GNSS config, flash, motor/bay test.

## 4. Dependencies và prerequisites

Exact board/GNSS/datasheet, safe bench, propeller/actuator isolation, supervisor and stop authority.

## 5. Quyết định áp dụng

Read-only adapter; no command channel; model-specific parser gate.

## 6. Files

Reports/fixtures/adapter tests only after approval; never overwrite archive/firmware.

## 7. Tasks

Hash archive → verify UART ownership → synthetic NMEA/UBX → passive capture plan → parser/stale validation → safety review.

## 8. API/data contracts và lỗi

`NO_FIX`, bad checksum, timeout, sequence gap and unknown fields are explicit errors/statuses.

## 9. Quyền, secrets, privacy, safety

No motor/ARM commands; no secret/raw PII; physical setup and stop conditions documented before power.

## 10. Test plan

Synthetic parser fixtures first; passive hardware only with approval; no write/config tests.

## 11. Acceptance criteria

Evidence-based table complete; `BLOCKED` retained if model/wiring absent; no fabricated telemetry.

## 12. Evidence

Archive hash, datasheet, wiring photos, redacted capture and parser test output.

## 13. Rollback/failure handling

Unplug/disable adapter per approved procedure; preserve capture/evidence; no firmware rollback in this scope.

## 14. Definition of Done / gate

Qualified reviewer signs read-only boundary before SCOPE-06/07.
