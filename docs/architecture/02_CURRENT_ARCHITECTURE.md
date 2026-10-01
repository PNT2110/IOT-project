# Current architecture

## Runtime map

```text
Browser
  │ HTTPS through temporary quick tunnel
  ▼
Vite preview :5173 ── /api and /docs proxy ──► FastAPI :8765
                                                   │
                                                   ▼
                                             SQLite + Alembic
```

The FastAPI process binds loopback on the deployment host. The temporary
tunnel is the only public edge currently used for bounded testing.

## Implemented PC path

- Public health and public synthetic-zone reads.
- Registration, email verification challenge, TOTP enrollment and confirmation.
- Login staging through email OTP and TOTP.
- Session/authentication, role checks, account review and role-elevation
  workflows.
- Synthetic flight-request lifecycle, audit/history and read-only fake Pi
  adapters.
- React overview that proves the public API connection and displays synthetic
  public zones.

## Not connected to the active path

- Google-like interactive map and drawing/editing tools.
- Authenticated Web dashboard for the PC workflows.
- Pi AP/captive portal, camera stream and outbound device agent.
- ESP32 serial protocol, live GPS ingestion and firmware update pipeline.
- Ministry/external approval integration.
- Real flight command or arming path (intentionally absent).

## Important mismatch

The archived backend and frontend still contain endpoints such as
`/api/v1/status`, `/api/v1/telemetry/latest`, camera and serial routes. The
canonical PC server does not implement those legacy routes. They must not be
reintroduced by wiring the old UI directly to the new server.
