# SCOPE-08 — Deployment & hardening

## 1. Mục tiêu và bàn giao

Legal/privacy/security/network/TLS/backup/DR review trước public exposure.

## 2. Bối cảnh/trạng thái

Hiện chưa có public deployment; mọi claim security/authority còn pending review.

## 3. In scope / out of scope

In: staged deployment/hardening/go-no-go. Out: unapproved public launch.

## 4. Dependencies và prerequisites

All prior scopes approved, authorized data, threat model, restore drill, SBOM/security tests, operations owner.

## 5. Quyết định áp dụng

ADR-009; fail-closed exposure gate and reversible rollout.

## 6. Files

Deployment manifests/runbooks/reports only; no secret-bearing files.

## 7. Tasks

Exposure decision → TLS/proxy → firewall/rotation → backup/restore → monitoring/incident response → security review → staged pilot.

## 8. API/data contracts và lỗi

Health/readiness must not leak secrets; rollback/version errors explicit.

## 9. Quyền, secrets, privacy, safety

Legal disclaimer, provenance, retention, least privilege, no actuator/public authority claim.

## 10. Test plan

TLS, auth/IDOR, firewall, backup restore, dependency/SBOM, incident drill and rollback rehearsal.

## 11. Acceptance criteria

Explicit go/no-go; no unresolved P0; rollback rehearsed; data provenance visible. Failure keeps private.

## 12. Evidence

Review records, test logs, restore checksum, config manifest, approval.

## 13. Rollback/failure handling

Withdraw exposure, restore previous release and preserve audit/evidence; do not delete blindly.

## 14. Definition of Done / gate

Operations/legal/security owners approve before any public decision.
