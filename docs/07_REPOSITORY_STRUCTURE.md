# SCOPE-00 — Repository structure proposal

SCOPE-00 chỉ tạo `docs/`. Không tạo `server/`, `pi5/`, `esp32/` hay copy firmware.

## Current inventory

- Root verified: `/home/pnt/IOT`.
- `FC_can_bang.zip` hiện có ở root.
- `HEAD` có lịch sử `backend/`, `frontend/`, `deploy/`, `tests/`, `FC_can_bang/`; worktree hiện đánh dấu phần lớn là deleted/modified. Đây là lịch sử repository, không phải bằng chứng implementation đang tồn tại trên disk.
- `docs/` chưa tồn tại trước SCOPE-00 và được tạo bởi scope này.

## Target after approval

```text
IOT/
├── docs/                 # SCOPE-00, design source of truth
├── contracts/            # versioned JSON/OpenAPI schemas
├── server/               # PC local app, SCOPE-01+
│   ├── app/
│   ├── migrations/
│   └── tests/
├── pi5/                  # only after Pi scopes
│   ├── app/
│   ├── network/
│   └── tests/
├── firmware-audit/       # reports/fixtures, not production firmware
└── tools/                # non-destructive inspection tools
```

## Rules

1. Keep `docs/` relative links stable.
2. Separate production-like code from test fixtures and hardware evidence.
3. Never commit secrets, raw email OTP, TOTP seed, recovery codes, or private personal data.
4. Archive checksum and evidence manifest belong in a report, not in source code.
5. Do not resolve current dirty worktree by restore/reset; owner must decide.
