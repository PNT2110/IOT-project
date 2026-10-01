# SCOPE-03 N4 Failure/Recovery Report

**STATUS: `OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED`**  
**Captured:** 2026-09-24 (Asia/Ho_Chi_Minh)  
**Gate:** N4 — AP remains reachable during verified STA/upstream failure.

## Authorization and prerequisites

The owner supplied a completed bounded approval for the N4 test. The current prompt reports that the baseline matched the target and that the failure/recovery sequence completed successfully. Codex did not independently execute or observe the Pi session, so the technical result remains owner-attested rather than `CODEX_TESTED_LIVE`.

Required before execution:

- local console is usable and independent of `wlan0`;
- `wlan0` upstream profile and `F450-1RADIO` AP profile are read-only verified;
- `ap0` gateway is verified as `192.168.4.1/24` and a real client is connected;
- baseline is captured with redacted addresses/identifiers;
- no update, transfer, firmware or unrelated operation is active;
- rollback operator and restore path are present.

## Exact plan — proposal only, do not execute

The profile names below are owner-provided and must be re-verified by a separately authorized read-only audit. The block is not an authorization:

```bash
# Read-only baseline; redact IP/MAC/client identifiers before storage.
nmcli --fields DEVICE,TYPE,STATE,CONNECTION device status
ip -br link
ip -br addr
ip route
systemctl is-active f450-ap.service
systemctl is-enabled f450-ap.service

# Failure injection — NOT AUTHORIZED. Only after owner approval and verification.
nmcli connection down id netplan-wlan0-C25B

# During failure: observe AP/client continuity using the approved redacted method.
# Do not stop f450-ap.service, down ap0, delete profiles, reset NetworkManager,
# flush routes/firewall or reboot.

# Recovery — NOT AUTHORIZED. Only after the continuity result is recorded.
nmcli connection up id netplan-wlan0-C25B
```

The exact command list must be revalidated against the live profile identity before execution. Do not copy a password, PSK, saved profile, raw MAC/BSSID or full log into the repository.

## Reconciled owner-provided baseline

```text
DEVICE=Raspberry Pi 5 Model B Rev 1.0
KERNEL=6.18.50+rpt-rpi-2712
STA=wlan0 / netplan-wlan0-C25B / managed / upstream 192.168.1.0/24 / SSID C25B
AP=ap0 / F450-1RADIO / AP / SSID F450 / 192.168.4.1/24
PHY_CHANNEL=phy#0 / channel 36 / 5180 MHz / 80 MHz
SERVICE=f450-ap.service active and enabled
REAL_CLIENT=present on ap0
DEFAULT_ROUTE=through wlan0
EVIDENCE_CLASS=OWNER_PROVIDED
```

## Reconciled completion and protocol status

The owner stated the sequence completed successfully. No raw failure-side/recovery-side transcript is available in the repository for each required observation, so record:

```text
OWNER_ATTESTED_COMPLETION
N4_TECHNICAL_BEHAVIOR=OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED
N4_PROTOCOL_COMPLIANCE=DEVIATION_RECORDED
PROTOCOL_DEVIATION=N4 failure injection was initiated from SSH over wlan0 rather than from the approved local-console-only mutation path.
```

## Required observations

During failure: `wlan0` upstream unavailable; Internet/upstream probe fails; `ap0` remains present; F450 remains available; client remains associated or reconnects; client reaches `192.168.4.1`; DHCP/local path remains usable; console recovery remains usable; no uncontrolled restart loop occurs.

After recovery: `wlan0` reconnects; upstream address/default route and approved Internet probe recover; F450 remains available; `ap0` remains at the approved gateway; client local access remains functional; no manual AP rebuild is required.

## Result

```text
FAILURE_INJECTED=OWNER_ATTESTED_COMPLETION
AP_CONTINUITY=OWNER_ATTESTED_NOT_SEPARATELY_EVIDENCED
REAL_CLIENT_EVIDENCE=OWNER_ATTESTED_NOT_SEPARATELY_EVIDENCED
STA_RECOVERY=OWNER_ATTESTED_COMPLETION
TIMESTAMPS=OWNER_PROVIDED_SUMMARY_NOT_RAW
ROLLBACK=OWNER_ATTESTED_NOT_SEPARATELY_EVIDENCED
N4=OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED
N4_PROTOCOL_COMPLIANCE=DEVIATION_RECORDED
FAILURE_OBSERVATIONS=OWNER_ATTESTED_NOT_SEPARATELY_EVIDENCED
RECOVERY_OBSERVATIONS=OWNER_ATTESTED_NOT_SEPARATELY_EVIDENCED
```

No `N4=PASS_LIVE_REAL_CLIENT` is claimed from owner assertion, service status, `ap0` existence, mock tests or the plan alone.
