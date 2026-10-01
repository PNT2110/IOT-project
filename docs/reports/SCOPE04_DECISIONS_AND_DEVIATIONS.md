# SCOPE-04 Decisions and Deviations

## Decisions implemented

1. Pi-local USER/ADMIN identity is independent from the PC identity domain.
2. Authentication uses local password verification, an ephemeral local MFA
   challenge, secure session cookies, CSRF validation for cookie mutation, and
   bounded authentication failures. No email, PC token, password, OTP, or
   secret is logged.
3. Camera access is read-only and adapter based. The default explicit path is
   `/dev/video0`; `/dev/video1` is rejected as the inventoried metadata node.
   Frames are bounded in memory and are not recorded or persisted.
4. Map data is a local fixture/cache with provenance and stale state. It has no
   fetch method, so upstream loss cannot trigger an implicit network request.
5. Telemetry is versioned and marked `source=MOCK`; absent values are
   `UNAVAILABLE`. The 3D view disables itself if orientation fields are absent.
6. `PiWebConfig` rejects wildcard/public binds. This implementation only
   creates an ASGI app; it does not start a listener.

## Deviations and limitations

- The camera implementation is a repository adapter and mock test surface;
  no live frame was opened or captured in this turn.
- The SCOPE-04 UI is a dependency-free local read-only shell plus typed API,
  not a production browser bundle. Browser visual QA and Pi runtime smoke are
  live-deployment work.
- The local MFA challenge is an ephemeral prototype primitive. Production
  enrollment, persistence policy, and operational secret provisioning require
  a separately approved deployment design.
- No PC↔Pi TLS/device identity or protected-data retention decision was
  silently added. Those remain outside this local-only implementation.
- SCOPE-03 N4 evidence remains owner-attested with its recorded protocol
  deviation; this work does not alter that evidence.
