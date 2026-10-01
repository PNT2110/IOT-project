# Risks and technical debt

| Severity | Risk | Affected area | Action |
|---|---|---|---|
| Critical | Public edge is temporary; no production security gate | deployment | keep bounded; add named HTTPS/reverse proxy before production |
| High | Two historical stacks use incompatible API shapes | Web/server | remove legacy imports through a deliberate adapter migration |
| High | Pi/ESP32 are archived, not active runtime modules | device integration | restore incrementally under explicit boundaries |
| High | Real external authority and permit semantics are unspecified | flight approval | implement a simulator/contract first; no real permit claim |
| High | No local Git history | release safety | initialize repository/remote or use managed worktree before broad refactor |
| Medium | Local dependency installation is incomplete | developer workflow | add reproducible setup/CI and lockfile checks |
| Medium | UI currently proves public data only | frontend | implement auth and role-specific feature areas after API contracts |
| Medium | Fake mail and SQLite are development-only | operations | production mail, database backup and migration policy |
| Medium | GPS physical wiring/protocol configuration is unverified | ESP32/Pi | read-only hardware inventory before flashing |
