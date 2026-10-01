# SCOPE-03 Live Network Evidence

**STATUS: `OWNER_PROVIDED + OWNER_ATTESTED_COMPLETION — CODEX_LIVE_OBSERVATION_PENDING`**  
**Captured:** 2026-09-24 (Asia/Ho_Chi_Minh)  
**Boundary:** The current prompt supplied a redacted summary of live baseline facts and the owner's completion statement. Codex did not independently connect to or execute commands on the Pi in this turn.

## Evidence classification

| Evidence item | Source | Status | What it proves | What it does not prove |
|---|---|---|---|---|
| Target topology `wlan0` STA + `ap0` F450 AP | Owner-directed prompt | `OWNER_OVERRIDE` | Owner's intended architecture | Runtime role, PHY mapping or current state |
| `netplan-wlan0-C25B` upstream profile | Owner-directed prompt | `OWNER_PROVIDED` | Claimed profile identity | Profile content, active state or credentials |
| `F450-1RADIO` AP profile | Owner-directed prompt | `OWNER_PROVIDED` | Claimed AP profile identity | Activation, channel, DHCP/DNS or client reachability |
| `f450-ap.service` enabled/oneshot | Owner-directed prompt | `OWNER_PROVIDED` | Claimed boot design | Unit contents, exit status or boot persistence observed by Codex |
| Same PHY/channel | Owner-directed prompt | `OWNER_PROVIDED` | Claimed hardware/runtime behavior | Independent capability or channel measurement |
| Real client received AP address | Owner-directed prompt | `OWNER_PROVIDED` | Claimed client/DHCP event | Client identity, exact raw output, persistence or N4 continuity |
| Default route through `wlan0` | Owner-directed prompt | `OWNER_PROVIDED` | Claimed upstream route | Current route or Internet probe |
| Prior Pi inventory | `SCOPE03_PI_READONLY_INVENTORY_RESULT.md` | `PRIOR_SSH_OBSERVATION` | Prior Pi model/OS/interface-driver snapshot | Current topology, new profiles or N4 |
| PC test suite | Local PC execution, 2026-09-24 | `MOCK_TESTED` | 31 offline tests pass | Any Pi/network behavior |

## Owner-provided live baseline before N4

The current prompt reports the following as already demonstrated on the target Pi. These facts are recorded as `OWNER_PROVIDED`, not `CODEX_OBSERVED_READ_ONLY`, because the raw terminal output is not present in the repository:

| Fact | Owner-provided value | Evidence class | Limitation |
|---|---|---|---|
| Device | Raspberry Pi 5 Model B Rev 1.0 | `OWNER_PROVIDED` | No raw transcript retained here. |
| Kernel | `6.18.50+rpt-rpi-2712` | `OWNER_PROVIDED` | Differs from the prior SSH snapshot's kernel; both remain time-scoped evidence. |
| STA | `wlan0`, `netplan-wlan0-C25B`, managed, upstream address in `192.168.1.0/24`, SSID `C25B` | `OWNER_PROVIDED` | Exact raw address/SSID output is not stored. |
| AP | `ap0`, `F450-1RADIO`, AP, SSID `F450`, gateway `192.168.4.1/24` | `OWNER_PROVIDED` | No raw client identifier stored. |
| PHY/channel | `wlan0` and `ap0` under `phy#0`, channel 36 / 5180 MHz, 80 MHz width | `OWNER_PROVIDED` | Not independently observed by Codex. |
| Service | `f450-ap.service` active and enabled | `OWNER_PROVIDED` | Unit contents and exit transcript not retained. |
| Real client | Client present on `ap0` | `OWNER_PROVIDED` | Raw MAC/BSSID/client identifier omitted. |
| Default route | Through `wlan0` | `OWNER_PROVIDED` | No raw route transcript retained. |

## Owner-attested N4 completion

The owner stated that the remaining failure/recovery sequence completed successfully. Classify this as:

```text
OWNER_ATTESTED_COMPLETION
N4_TECHNICAL_BEHAVIOR=OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED
```

The current workspace does not contain separate redacted failure-side and recovery-side observations for every required item, so this statement does not become `CODEX_TESTED_LIVE` or `PASS_LIVE_REAL_CLIENT`.

The prompt also states that the approved `nmcli connection down id netplan-wlan0-C25B` mutation was initiated from an SSH session over `wlan0`, rather than from the approved local-console-only mutation path. Record this explicitly:

```text
N4_PROTOCOL_COMPLIANCE=DEVIATION_RECORDED
PROTOCOL_DEVIATION=N4 failure injection was initiated from SSH over wlan0 rather than from the approved local-console-only mutation path.
```

## Explicitly not promoted to live evidence

The following remain unverified: AP broadcast, real F450 association, DHCP continuity, same-channel capability, upstream failure behavior, recovery via local console, `f450-ap.service` contents/status, profile contents, subnet conflict, Internet reachability and central-server reachability.

No raw client MAC/BSSID, password, PSK, OTP/TOTP, SSH secret, private key or credential is stored here. The newly supplied login details are intentionally not repeated or recorded.

## Current live boundary

```text
CODEX_OBSERVED_LIVE=NONE_IN_THIS_TURN
CODEX_TESTED_LIVE=NONE_IN_THIS_TURN
OWNER_PROVIDED_LIVE_EVIDENCE=BASELINE_SUMMARY
OWNER_ATTESTED_COMPLETION=RECEIVED
N4_TECHNICAL_BEHAVIOR=OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED
N4_PROTOCOL_COMPLIANCE=DEVIATION_RECORDED
LIVE_NETWORK_AUTHORIZATION=GRANTED_FOR_BOUNDED_TEST
N4=NOT_FULLY_EVIDENCED
SCOPE04=READY_FOR_OWNER_START_NOT_OPENED
```
