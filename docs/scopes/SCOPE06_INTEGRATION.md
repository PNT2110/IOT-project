# SCOPE-06 — Simulated integration

## 1. Mục tiêu và bàn giao

PC↔Pi↔ESP telemetry read-only end-to-end with mocks/safe adapter.

## 2. Bối cảnh/trạng thái

Chỉ mở sau khi contracts và evidence từng miền đạt gate.

## 3. In scope / out of scope

In: authenticated sync/cache/status/telemetry. Out: public deployment, legal authority, actuator/flight path.

## 4. Dependencies và prerequisites

SCOPE-02, 04, 05 PASS; device identity/cert test setup.

## 5. Quyết định áp dụng

Versioned contracts, stale-first display, REST canonical + realtime adapter.

## 6. Files

Integration fixtures/tests/config only; no firmware or live deployment edits.

## 7. Tasks

Version negotiation → authenticated sync → offline replay → seq/stale → simulated workflow display → failure injection.

## 8. API/data contracts và lỗi

Auth failure, schema mismatch, stale cache and sequence gap remain explicit; no silent downgrade.

## 9. Quyền, secrets, privacy, safety

Device identity rotation test; no server-to-actuator contract.

## 10. Test plan

PC down, Pi down, Internet down, replay, duplicate idempotency, bad telemetry and simulated approval.

## 11. Acceptance criteria

Server loss leaves Pi local; stale visible; approval cannot produce actuator request; all changes auditable.

## 12. Evidence

Trace logs, fixture hashes, contract versions, failure-injection report.

## 13. Rollback/failure handling

Disable integration adapter and preserve cache/report; revoke test identity if compromised.

## 14. Definition of Done / gate

Owner accepts end-to-end simulated evidence before SCOPE-07.
