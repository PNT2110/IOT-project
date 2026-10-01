# SCOPE-00 — Kiến trúc hệ thống

## Context và trust boundaries

```mermaid
flowchart LR
  Guest[Guest browser] -->|public read only| PC[PC server / API]
  User[PC User/Pending/Operator] --> PC
  Admin[PC Admin/Owner] --> PC
  PiUser[Pi USER/ADMIN browser] --> Pi[Pi 5 web]
  PC <--> |authenticated data API only| Pi
  Pi -->|read-only adapter| FC[ESP32 flight controller]
  FC --> GNSS[GNSS module]
  Pi --> Cam[USB webcam]
  PC --> DB[(DB + audit + object storage)]
  PC --> Email[Email provider]
  PC --> MapSrc[Authorized map/data source]
  PC -.->|no direct authority| Sim[Simulated external authority]
  Internet[External network] --> Pi
  Internet --> PC
  classDef trust fill:#eef,stroke:#335;
  class PC,Pi,FC,DB trust;
```

Trust boundaries: public browser↔PC public API; PC↔Pi authenticated integration; Pi↔USB/serial devices; application↔OS/network services; source data↔licensed content. “Simulated external authority” is a label only, not an integration endpoint.

## Module view

```mermaid
flowchart TB
  subgraph PC
    UI[React/TS UI]
    API[FastAPI REST + realtime adapter]
    Auth[Auth/RBAC/session]
    Geo[Geo domain + provenance]
    WF[Simulated workflow]
    Audit[Append-only audit]
    DB[(SQLite local; PostGIS gate)]
    UI --> API
    API --> Auth
    API --> Geo
    API --> WF
    API --> Audit
    Auth --> DB
    Geo --> DB
    WF --> DB
    Audit --> DB
  end
  subgraph Pi
    Net[NetworkManager/AP/STA state]
    Portal[Config/recovery portal]
    PiAuth[Local auth/RBAC]
    Cache[Map/status cache]
    CamA[Camera adapter]
    Tele[Telemetry adapter]
    PiWeb[Pi web]
    PiWeb --> PiAuth
    PiWeb --> Cache
    PiWeb --> CamA
    PiWeb --> Tele
    Portal --> Net
  end
  subgraph FC
    Read[Read-only serial boundary]
    FW[Existing firmware]
    GNSS[GNSS]
    Read --> FW
    GNSS --> FW
  end
  API <-->|versioned authenticated contract| PiWeb
  Tele --> Read
```

## Safety boundary

PC workflow output terminates at `SIMULATED` status. Pi may display telemetry and status; no API schema, route, websocket, serial adapter or UI action accepts an ARM/DISARM command. Any future firmware/flight-mode work requires SCOPE-07 and explicit safety review.

## Identity flow

```mermaid
flowchart TD
  B[First-run Owner bootstrap] --> O[Owner account + MFA]
  R[Register] --> E[Email verification]
  E --> T[TOTP enrollment + recovery code hash]
  T --> P[PC Pending]
  P -->|approved by policy| U[PC user role]
  PR[Pi register] --> PT[Email verify + TOTP]
  PT --> PU[Pi USER]
  PU -->|explicit request| PA[Pi ADMIN approval]
  L[Login] --> F1[Password]
  F1 --> F2[Email OTP]
  F2 --> F3[TOTP/recovery policy]
  F3 --> S[Staged session]
  F2 -. provider offline: AUTH_UNAVAILABLE .-> X[Denied/no elevation]
```

Email verification is not inferred from an existing browser session. PC and Pi flows remain separate.

## Data flow and operations

```mermaid
sequenceDiagram
  participant C as Client
  participant P as PC API
  participant D as DB and Audit
  participant I as Pi
  participant F as ESP32 read-only
  C->>P: authenticated map/request
  P->>D: validate and audit
  P-->>C: SIMULATED status only
  I->>P: versioned authenticated sync
  P-->>I: authorized data + provenance
  F-->>I: telemetry frames only
  I-->>C: stale/units/availability marked
```

Operational future sequence: boot AP/local web → start status adapters → load last-known-good cache → attempt STA → probe Internet → probe central server → expose explicit states → persist redacted logs/audit → backup by policy. Failure keeps AP/local service alive where possible; it never triggers actuator behavior.

## Offline-first behavior

| Condition | Required behavior |
|---|---|
| Internet down | AP, local Pi web, camera and cached internal data continue; show `internet_reachable=false`. |
| PC unreachable | Pi keeps local web/camera/last telemetry; show `central_server_reachable=false`; cache marked stale. |
| Email provider unavailable | No new MFA bypass; show `AUTH_UNAVAILABLE`, preserve audit-safe error. |
| GNSS no valid fix | Coordinates `UNAVAILABLE`/`STALE`; never fabricate a point. |
| Map cache old | Visible `stale_at`/age and provenance; no legal validity claim. |
