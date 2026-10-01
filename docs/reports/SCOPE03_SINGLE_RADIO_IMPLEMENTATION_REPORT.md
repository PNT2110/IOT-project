# SCOPE-03 Single-Radio Implementation Report

**STATUS: `OWNER_OVERRIDE — OWNER_PROVIDED_LIVE_BASELINE — N4_ATTESTED_NOT_FULLY_EVIDENCED`**  
**Captured:** 2026-09-24 (Asia/Ho_Chi_Minh)  
**Evidence boundary:** PC repository reconciliation only; no new SSH session, Pi command or network mutation was performed.

## Owner override

The owner changed the target deployment profile from onboard AP + USB STA to a single onboard PHY:

```text
wlan0 -> managed STA -> upstream network
ap0   -> AP          -> F450 local recovery network
```

This is an `OWNER_OVERRIDE`, not `LIVE_OBSERVED` evidence. The previous design remains historical evidence and is not silently rewritten.

## Target architecture

| Element | Owner-directed target | Evidence class | Current limitation |
|---|---|---|---|
| PHY | One onboard Wi-Fi PHY | `OWNER_PROVIDED` | Physical mapping not independently observed in this turn. |
| Upstream interface | `wlan0`, managed/STA | `OWNER_PROVIDED` | Role must be verified from runtime state, not name. |
| Recovery AP | `ap0`, AP, SSID `F450` | `OWNER_PROVIDED` | AP presence, client association and broadcast not independently observed. |
| AP gateway | `192.168.4.1/24` | `OWNER_PROVIDED` | Overlap/DHCP range and runtime address not independently observed. |
| Channel | AP and STA share one channel | `OWNER_PROVIDED / UNVERIFIED` | Capability/channel/regulatory evidence is not in this PC workspace. |
| Upstream route | Default route remains via `wlan0` | `OWNER_PROVIDED` | No live route observation in this turn. |

## Proposed runtime behavior

The owner-described implementation uses a NetworkManager profile for `wlan0`, a NetworkManager profile for `F450-1RADIO`, and `f450-ap.service` to create `ap0` only when absent, determine the current STA channel, synchronize the AP band/channel, and activate the AP. Reusing `ap0` during ordinary stop/restart is recorded as an operational lesson, not yet as independently audited implementation evidence.

The following Pi paths were requested for read-only audit but were not read in this turn:

```text
/usr/local/sbin/f450-ap.sh
/etc/systemd/system/f450-ap.service
NetworkManager metadata for netplan-wlan0-C25B and F450-1RADIO
```

No service restart, profile activation/deactivation, `ap0` deletion, package installation or reboot was performed.

## DHCP/DNS and recovery boundary

The target requires DHCP/DNS to serve only the AP recovery network and must preserve local AP access when upstream STA/Internet fails. Exact service ownership, firewall behavior, manual URL, snapshot location and rollback commands remain `UNVERIFIED`. PC↔Pi status exchange remains blocked until device identity/TLS and retention/legal hold are decided.

## Owner-provided live baseline and N4 closeout claim

The current owner evidence summary reports Raspberry Pi 5 Model B Rev 1.0, kernel `6.18.50+rpt-rpi-2712`, managed `wlan0` using `netplan-wlan0-C25B`, AP `ap0` using `F450-1RADIO`, F450 gateway `192.168.4.1/24`, both interfaces under `phy#0` on channel 36 / 5180 MHz with 80 MHz width, `f450-ap.service` active/enabled, a real client present and the default route through `wlan0`. These are `OWNER_PROVIDED`, not Codex-observed facts.

The owner also attested that the N4 failure/recovery sequence completed successfully. The required failure/recovery observations are not present as separate raw or redacted transcripts in this workspace, so the result remains `OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED`. The prompt records a protocol deviation: failure injection was initiated over SSH via `wlan0` instead of the approved local-console-only mutation path.

## Files changed in this documentation turn

- `docs/ADR/ADR-SCOPE03-SINGLE-RADIO-AP-STA.md` — records the owner override and rollback/trade-offs.
- `docs/12_NETWORK_ARCHITECTURE.md` — updates the living target profile while marking live validation pending.
- `docs/03_TECHNOLOGY_DECISIONS.md` — adds the current owner override without rewriting ADR-006.
- `docs/scopes/SCOPE03_PI_NETWORK.md` — updates living SCOPE-03 target wording.
- `docs/01_REQUIREMENTS.md` and `docs/04_ASSUMPTIONS_AND_OPEN_QUESTIONS.md` — classify the new profile as owner override pending validation.
- Current SCOPE-03 reports created below are evidence/handoff documents only.

No historical report, firmware, runtime implementation or SCOPE-04/05/06 artifact was modified.

## Gate consequence

```text
N1=PASS_PC_MOCK
N2=READY_FOR_LIVE_EVIDENCE
N3=PASS_PC_MOCK / LIVE_NOT_RUN
N4=OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED
N4_PROTOCOL_COMPLIANCE=DEVIATION_RECORDED
N5=DOCUMENTATION_IN_PROGRESS
LIVE_NETWORK_AUTHORIZATION=GRANTED_FOR_BOUNDED_TEST
```
