# Data model review

## Reusable current entities

The current migrations already cover the core PC workflow: users, terms and
verification challenges, sessions, zones and zone sources, role-elevation
requests, simulated flight requests, audit/history and capability grants.

## Target domains still missing

The following should be introduced only after the contract and migration
design is approved:

- `devices`: device identity, type, status, firmware version, last heartbeat,
  capabilities and public-key/credential metadata;
- `research_sessions`: operator, device, mode, lifecycle and artifact links;
- `telemetry_points`/`telemetry_events`: validated measurements, sequence,
  timestamp, source and stale/duplicate state;
- `approval_requests`: explicit separation of account, role, zone and flight
  approval decisions;
- `firmware_releases`/`firmware_deployments`: signed package metadata,
  compatibility and rollout result.

Do not add migrations merely to match the target list. First map each field to
an existing model or a concrete use case and define rollback/data retention.
