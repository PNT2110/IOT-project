# Target architecture

The target is a modular monorepo with one authority: the PC server. The first
implementation should reuse working PC auth/workflow code and migrate one
boundary at a time.

```text
Internet / private overlay
          │ HTTPS / WSS
          ▼
PC public gateway
  ├── Web application
  ├── Auth + RBAC + approvals
  ├── Zones/map authority
  ├── Flight/research sessions
  ├── Device registry + telemetry ingestion
  ├── Audit/observability
  └── SQLite now → PostgreSQL-ready boundary later
          ▲ outbound HTTPS/WSS
          │
      Pi 5 edge node
  ├── AP/captive network setup
  ├── local auth/session boundary
  ├── USB camera read-only stream
  ├── PC server client/cache
  ├── telemetry adapter
  └── firmware package verifier
          ▲ serial/UART
          │
      ESP32 + GPS
  ├── stabilization/control firmware
  ├── GNSS parser/health
  ├── versioned telemetry framing
  └── watchdog/fail-safe state
```

The PC must never expose its database, Pi-local service, serial device or
development server directly to the Internet. The Pi should initiate outbound
connections to the PC rather than requiring an exposed Pi API.
