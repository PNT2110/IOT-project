# ADR-SCOPE03 — Single-Radio AP + STA Deployment Profile

**Status:** `OWNER_OVERRIDE — LIVE_VALIDATION_PENDING`  
**Date:** 2026-09-24 (Asia/Ho_Chi_Minh)  
**Scope:** SCOPE-03 only

## Context

The historical SCOPE-03 design used the onboard Wi-Fi adapter for the recovery AP and a USB Wi-Fi adapter for the upstream STA. Existing historical reports, mock contracts and earlier design decisions remain valid snapshots of that design.

The owner has now directed a different target deployment profile: one onboard Wi-Fi PHY should provide both the upstream managed STA and the local recovery AP. This is recorded as an owner architecture override. It is not independently observed by Codex in this turn and is not live-network authorization.

## Old architecture — historical baseline

```text
onboard Wi-Fi  -> AP / recovery
USB Wi-Fi      -> upstream STA
```

This was the previous design, not an implementation error to be rewritten out of history. Historical reports and mock tests using `onboard_ap` and `usb_sta` remain historical evidence and must not be relabeled as evidence for the new profile.

## Owner decision and new deployment profile

```text
one onboard Wi-Fi PHY
  phy0
    +-- wlan0
    |     mode: managed / STA
    |     purpose: upstream network / Internet
    |
    +-- ap0
          mode: AP
          SSID: F450
          purpose: local recovery/access network
          IPv4 gateway: 192.168.4.1/24
```

The role mapping above is an `OWNER_OVERRIDE` target for the verified Pi deployment profile. It is not a universal Linux rule and must not be inferred from interface names alone.

## Concurrency and same-channel constraint

The owner-provided target evidence describes the active capability as:

```text
managed <= 1
AP <= 1
#channels <= 1
```

If independently confirmed, `wlan0` and `ap0` share one PHY and must use the same radio channel. Runtime behavior therefore needs to determine the current `wlan0` channel, select the corresponding 2.4 GHz or 5 GHz band, configure the F450 AP profile to the same channel, and activate the AP only after the profile is consistent.

This capability, the interface-to-physical mapping, regulatory domain and runtime channel are currently `OWNER_PROVIDED/UNVERIFIED`. `iw` was unavailable in the prior read-only session; no package installation is authorized by this ADR.

## Why USB STA is no longer the baseline

The owner explicitly changed the target topology to prioritize a single onboard-radio AP+STA recovery profile. The USB STA design remains the prior baseline for historical evidence and fallback analysis, but it is no longer the target deployment profile. This ADR does not claim that every USB adapter or every Pi driver supports the new topology.

## Operational consequences and trade-offs

- The AP and upstream STA contend for one PHY and one channel; throughput, airtime and reliability can be lower than with independent radios.
- A channel change or upstream roaming event may affect the AP client path; channel synchronization must be bounded and observable.
- The AP/local recovery path must remain separate from Internet and PC/server reachability signals.
- The current upstream route must remain on `wlan0` during ordinary AP operation; no role change may be inferred from the name alone.
- A local console or genuinely independent recovery path is required before any live mutation or N4 failure injection.
- DHCP/DNS ownership, subnet overlap, manual URL, identity/TLS and retention/legal-hold decisions remain explicit gates.

## Implementation direction

The owner-provided implementation description names `netplan-wlan0-C25B` as the managed upstream profile, `F450-1RADIO` as the AP profile and `f450-ap.service` as a oneshot activation path with runtime channel synchronization. These are `OWNER_PROVIDED` facts awaiting read-only audit. No Pi filesystem, systemd unit, NetworkManager profile or script was read by Codex in this turn. No service restart, profile change, `ap0` deletion or reboot is authorized.

The operational lesson supplied by the owner is to reuse an existing `ap0` during ordinary stop/restart and create it only when absent, allowing NetworkManager time to recognize it. This remains an implementation hypothesis until audited and tested.

## Rollback strategy

Before any live mutation, capture a redacted last-known-good state and name the operator, console path, snapshot location and stop criteria. Rollback must restore the prior profile/service state through the independent console path, preserve `ap0` during ordinary recovery, verify local AP access first, then verify STA/upstream recovery separately. Broad profile deletion, NetworkManager reset, firewall flush and blind reboot loops are prohibited.

## Effect on SCOPE-03 requirements

- N1 mock/state semantics remain valid but must not be treated as live evidence.
- N2 requires real evidence for managed `wlan0`, AP `ap0`, F450, gateway, same PHY/channel, route and DHCP/client association.
- N3 continues to require independent `external_wifi_connected`, `internet_reachable` and `central_server_reachable` signals.
- N4 still requires a real client during a controlled STA/upstream failure and successful local AP continuity/recovery.
- N5 documentation may record the owner override, but cannot become a technical pass without live evidence and owner decisions.

## Supersession map

The following are superseded as the target living architecture for the verified Pi profile, but are not deleted:

- the USB-STA target in `docs/12_NETWORK_ARCHITECTURE.md`;
- the USB-STA wording in `docs/scopes/SCOPE03_PI_NETWORK.md`;
- ADR-006's target topology in `docs/03_TECHNOLOGY_DECISIONS.md`.

The following remain untouched historical snapshots:

- `docs/reports/SCOPE03_FINAL_REPORT.md`;
- `docs/reports/SCOPE03_TEST_REPORT.md`;
- `docs/reports/SCOPE03_PI_READONLY_INVENTORY_RESULT.md`;
- prior SCOPE-03 handoffs and PC-mock contracts.

No historical `29 passed`, `31 passed`, mock-only, `N4=BLOCKED/NOT_RUN` or prior-session result is rewritten by this ADR.

## Boundary

This ADR authorizes documentation of the owner-directed architecture only. It does **not** authorize SSH, sudo, package installation, network/profile/service mutation, reboot, N4 execution, PC↔Pi exchange, public exposure or any later scope. SCOPE-04/05/06/07/08 remain unopened.
