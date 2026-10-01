# SCOPE-00 — Security architecture và threat model

## Assets

Accounts/MFA, PII in applications, internal map layers, simulated requests, audit evidence, Pi device identity, camera/telemetry, firmware provenance and network credentials.

## Trust-boundary threats and controls

| Boundary | Threat | Baseline control |
|---|---|---|
| Public ↔ PC | credential stuffing, IDOR, CSRF, map leakage | Argon2id, MFA, rate limits, object auth, CSRF, public allowlist. |
| PC ↔ Pi | spoofed device, replay, stale/forged status | TLS/mTLS or equivalent device identity, nonce/timestamp/idempotency, key rotation, schema validation. |
| AP client ↔ Pi | rogue client, shell injection, portal abuse | unique AP key, segmentation, firewall, allowlist operations, no request-to-shell, CSRF. |
| Pi OS ↔ services | privilege escalation, secret exposure | least-privilege service account, systemd sandboxing later, filesystem permissions, redacted logs. |
| Pi ↔ camera | stream exposure/DoS | authenticated local stream, resource caps, no raw device exposure. |
| Pi ↔ FC | malicious command or parser bug | read-only adapter, no command interface in contracts, frame limits, stale marker. |
| Firmware update | tampered/rollback artifact | signed/provenance metadata and compatibility gate; SCOPE-07 only. |
| Data source ↔ map | poisoned/outdated/unlicensed data | source allowlist, checksum, effective/retrieved timestamps, manual review. |

## Secret policy

Never hard-code or log passwords, email OTP, TOTP secret, recovery codes, Wi-Fi password, API token or private key. Use environment/secret store only in later scopes; protect encrypted-at-rest key separately. Test fixtures use obvious non-secret placeholders.

## Privacy

Minimize legal/license identifiers, location history and camera retention. Define purpose, access role, retention and deletion/legal hold before storing. Audit metadata must not include request body secrets. Public map response must be schema-separated from internal layers.

## Safety security invariant

Security controls protect system/data; they do not establish flight permission or certify flight safety. No fail-closed authentication path may be turned into an automatic in-flight disarm recommendation. Current prototype has no server-to-actuator path.
