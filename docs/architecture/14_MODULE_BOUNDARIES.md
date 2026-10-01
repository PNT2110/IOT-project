# Module boundaries — PC-first implementation

The repository stays operationally simple while separating product domains. A
domain may not reach into another domain's private implementation; it must use
an API or a versioned contract.

```text
PC / public gateway
├── server/       FastAPI, auth, RBAC, zones, approvals, audit, persistence
├── frontend/     React/Vite public map and authenticated PC workspaces
├── contracts/    Web/API/device DTOs and protocol versions
├── tests/        PC API, contract and integration tests
├── docs/         requirements, architecture, deployment and evidence reports
├── edge/pi5/     active local read-only edge package; live deployment still gated
└── firmware/     reserved ESP32 package; not active until board identity is verified
```

## Ownership

| Module | Owns | Must not own |
|---|---|---|
| `server/` | user identity, sessions, roles, zone policy, approval workflows, audit and storage | browser rendering, raw UART drivers, motor/ARM logic |
| `frontend/` | map presentation, forms, tabs and user interaction | authorization decisions, secrets, direct database/device access |
| `contracts/` | versioned schemas, units, event names and compatibility rules | ORM models, business rules, device drivers or credentials |
| `edge/pi5/` | local auth shell, camera adapter, cached map/telemetry views and bounded role requests | central account policy, public Internet trust decisions, actuator commands |
| `firmware/` | sensor acquisition, balance control, GNSS parser, watchdog and safe local state | account approval, email OTP, external permit decisions |

## Current implementation gate

The active PC modules are `server/`, `frontend/`, `contracts/`, `tests/`,
`docs/` and the local read-only foundation in `edge/pi5/`. Live Pi AP/captive
portal, USB camera, outbound PC sync and ESP32/GPS integration remain hardware
acceptance gates, while older material remains under `archive/`. This keeps a
mock adapter from being mistaken for a live device integration.

## PC-first delivery order

1. Public map/read-only shell and server-side authorization.
2. PC authentication, account approval, role elevation and flight-request UI.
3. Zone editor with geometry validation, audit and optimistic concurrency.
4. Versioned device/realtime contracts and simulation pipeline.
5. Pi 5 outbound edge client and camera/map workspace, after identity/network
   acceptance.
6. ESP32/GPS bench integration, only after board/pin evidence is recorded.
