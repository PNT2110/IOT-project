# CODEX SCOPE-04 Pi Web Implementation

**STATUS: `READY_FOR_OWNER_START — DO NOT AUTO-EXECUTE`**

Start only after the owner sends a separate explicit instruction to begin SCOPE-04 implementation. This prompt covers SCOPE-04 only; it does not open SCOPE-05/06/07/08.

## Entry state

- SCOPE-02 amendment: owner accepted current packet; PC/Pi identity domains remain separate.
- SCOPE-03: owner accepted the technical result/evidence class/deviation/no-rerun decision. Keep `N4_TECHNICAL_BEHAVIOR=OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED` and `N4_PROTOCOL_COMPLIANCE=DEVIATION_RECORDED`.
- Camera inventory: `PASS`; `/dev/video0` is the identified USB UVC capture node, `/dev/video1` metadata only.
- Pi-local identity: accepted local USER/ADMIN boundary; no federation.
- Local retention boundary: camera recording off, frame persistence none, mock telemetry ephemeral, no PC↔Pi PII/status sync.
- Device identity/TLS remains deferred until the first actual PC↔Pi communication scope.

## Allowed SCOPE-04 implementation

Implement and test only:

- Pi-local authenticated auth/session boundary;
- camera adapter for the verified device with typed unavailable/error states and resource limits;
- authenticated local camera stream only when explicitly scoped, with recording and frame persistence disabled by default;
- provenance-bearing map cache with visible stale labels and approved/licensed source boundary;
- clearly labeled mock telemetry; unknown fields become `UNAVAILABLE`;
- 3D view from verified fields only;
- upstream-down/local-service tests;
- role, CSRF and rate-limit tests;
- rollback/disable behavior for optional camera/3D adapters.

## Required safety and privacy invariants

- PC identity and Pi identity remain separate; Pi ADMIN cannot become PC Owner.
- No PC↔Pi PII/status exchange or device federation.
- No public bind/exposure.
- No command endpoint, arbitrary shell execution or authority/approval route.
- No ARM/DISARM, actuator, flight-control or firmware route.
- No ESP32/GNSS/firmware access.
- No invented telemetry; preserve stale/unknown semantics.
- Keep raw camera frames out of persistence unless a new owner decision explicitly changes the retention boundary.

## Stop conditions

Stop if implementation requires unresolved device identity/TLS, protected persistence, camera permission changes, public exposure, PC↔Pi data exchange, later-scope work or any control/actuator path. Produce separate implementation/test/final reports with evidence classes and do not relabel mock results as live hardware evidence.
