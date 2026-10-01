# SCOPE-03 — Live change request (planning only)

**STATUS: `NOT AUTHORIZED — DO NOT EXECUTE`**

This document is a request template, not an executable runbook. No command below authorizes SSH, sudo or network change.

## Required owner-provided facts

- Pi model/RAM/OS/kernel/architecture: `UNVERIFIED`
- Pi address/username/access method: `UNVERIFIED` — do not infer from history
- Onboard AP interface and USB STA interface/chipset/driver/modes: `UNVERIFIED`
- Current subnet/router/SSID/DHCP/DNS/regulatory domain: `UNVERIFIED`
- Lab boundary, time window and responsible person: `UNVERIFIED`
- Independent console/recovery path: `UNVERIFIED`

## Proposed scope to approve explicitly

Only after the facts above are verified, owner may approve a numbered list of exact changes such as: temporary AP profile, temporary STA profile, DHCP/DNS service configuration, firewall segmentation, manual recovery URL and any service restart/reboot. Unlisted operations are not approved. `192.168.4.1/24` is not pre-approved; overlap must be measured first.

## Evidence and stop conditions

Capture redacted before/after status, one step at a time, from a real lab client. Stop if AP/manual URL, console, expected interface identity, subnet separation, DHCP/DNS behavior or rollback state is unclear. Never include PSK, tokens, cookies, private keys or unnecessary MAC/topology data.

## Approval fields

```text
LIVE_NETWORK_AUTHORIZATION: NOT_GRANTED
PI_READ_ONLY_INVENTORY_AUTHORIZATION: NOT_GRANTED
OWNER:
DATE/TIME WINDOW:
RESPONSIBLE OPERATOR:
INDEPENDENT RECOVERY PATH VERIFIED: NO
APPROVED CHANGES:
APPROVED ROLLBACK:
```
