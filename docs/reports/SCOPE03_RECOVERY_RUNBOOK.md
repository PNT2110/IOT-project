# SCOPE-03 — Recovery runbook (planning only)

**STATUS: `NOT AUTHORIZED — DO NOT EXECUTE`**

This is a review artifact. It must not be executed until the owner approves the live change request and a person is physically/independently present at the Pi.

## Before any live change

1. Confirm independent console/out-of-band recovery; an SSH session over the interface being changed does not qualify.
2. Record a redacted last-known-good snapshot of interface identity, address/subnet, route, DHCP/DNS/firewall and AP/manual URL.
3. Verify upstream subnet does not overlap the proposed private AP subnet. Do not assume `192.168.4.1/24`.
4. Confirm one small change at a time, a real client for AP observation and a stop operator.

## Failure handling

- If STA association/DHCP fails: keep AP unchanged, stop retries, restore the previous STA profile only through the approved console/operator path.
- If Internet is down: do not infer AP or PC failure; retain local recovery and record independent signals.
- If PC is down: do not infer Internet failure; mark central status unknown/down with timestamp and stale semantics.
- If AP/manual URL or independent console becomes unreachable: stop all remote attempts and use the approved console procedure.
- Do not run broad reset, delete profiles, alter firewall/route or reboot unless specifically listed in the approved change request.

## After rollback

Verify AP reachability from the real client, last-known-good STA state, DHCP/DNS/manual URL, no unintended forwarding/SSH exposure, and clean teardown. Redact evidence before storing it. If any check is uncertain, mark the gate `BLOCKED`, preserve evidence and wait for owner direction.
