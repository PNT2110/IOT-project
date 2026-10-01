# SCOPE-00 — Deployment strategy

## Staged environments

`local-dev` → `local-integration` → `Pi-lab` → `private pilot` → legal/security review → only then public exposure decision. SCOPE-01 remains localhost/local-only. No public server is started in SCOPE-00.

## Future PC deployment gates

Threat model, TLS certificate/renewal, reverse proxy isolation, firewall, least privilege, backup/restore drill, dependency/SBOM review, rate limits, privacy/retention, authorized map data and incident response. CGNAT, inbound exposure and remote administration must be resolved explicitly; never publish through an ad-hoc port forward.

## Future Pi deployment gates

Pin OS/image and USB device inventory, systemd sandbox, AP+STA recovery, secret provisioning, camera permissions, disk health, time sync, logs/rotation, update/rollback and physical access assumptions. SSH is not used in SCOPE-00.

## Rollback

Use versioned artifacts/config manifests and a tested previous release. Preserve audit/evidence; cleanup must be manifest-based and reversible where practical. Firmware rollback is SCOPE-07 only.
