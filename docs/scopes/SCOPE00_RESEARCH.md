# SCOPE-00 — Research & Architecture

## 1. Mục tiêu/bàn giao

Bàn giao bộ tài liệu kiến trúc, nghiên cứu, audit archive và prompt SCOPE-01. Không có code/hardware mutation.

## 2. Trạng thái

Archive tồn tại và đã đọc read-only; model board/GNSS/Pi runtime/API license còn `BLOCKED`/`UNVERIFIED`.

## 3. In/out

**In:** inventory, primary-source research, ADR, diagrams, contracts, roadmap, open questions. **Out:** code, install, SSH, flash, public service, motor/flight test, real authority request.

## 4. Dependencies và prerequisites

User-provided prompt và `FC_can_bang.zip`; web sources listed in `02_RESEARCH_REPORT.md`.

## 5. Quyết định kiến trúc áp dụng

ADR-001…009 tại `03_TECHNOLOGY_DECISIONS.md`; offline-first, separate identities, read-only telemetry, simulated workflow.

## 6. Files tạo/sửa/không sửa

Tạo/sửa chỉ `docs/**/*.md`. Không sửa source, archive, hardware config.

## 7. Tasks triển khai/nghiên cứu

1. Inventory repo/archive → tables in overview/audit.  
2. Research primary sources → cited report.  
3. Design contracts/diagrams → architecture/API docs.  
4. Define scopes/risks/tests → roadmap/scope docs.  
5. Quality check links/status → final handoff.

## 8. API/data contracts và chính sách lỗi

Contracts ở `../09_API_CONTRACTS.md`; SCOPE-00 không tạo endpoint và không chạy server.

## 9. Quyền, secrets, privacy và safety

Không thu thập secret/PII mới; không truy cập phần cứng; simulated/read-only boundary được ghi trong architecture.

## 10. Test plan

Kiểm tra tĩnh danh sách file, link tương đối, nhãn evidence, Mermaid và archive inventory; không có hardware test.

## 11. Acceptance criteria

Docs non-empty, claims labeled, diagrams/contracts/scopes present, blockers/questions recorded, no implementation mutation.

## 12. Required evidence

Archive listing/hash, git status before/after, source citations, file manifest, review checklist.

## 13. Rollback/failure handling

Chỉ xem xét xóa tài liệu mới sau owner review; không xóa source/evidence/dữ liệu cũ và không reset worktree.

## 14. Definition of Done / exit gate

Chủ dự án duyệt SCOPE-00; nếu chưa duyệt thì SCOPE-01 bị khóa.
