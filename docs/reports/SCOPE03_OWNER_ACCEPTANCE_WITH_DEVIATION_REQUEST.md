# SCOPE-03 Owner Acceptance with Protocol Deviation Request

**STATUS: `OWNER_ACCEPTED_WITH_DEVIATION — 2026-09-24`**

The current SCOPE-03 evidence is an owner-provided baseline plus owner-attested N4 completion. The failure injection was reported as initiated from SSH over `wlan0`, while the approval required local-console-only mutation. The deviation is recorded; no technical pass is invented.

## Owner decision block

```text
OWNER_ACCEPTS_SCOPE03_TECHNICAL_RESULT=yes / no
OWNER_ACCEPTS_N4_EVIDENCE_CLASS=yes / no
OWNER_ACCEPTS_PROTOCOL_DEVIATION=yes / no
OWNER_ACCEPTS_NO_N4_RERUN=yes / no
```

If any answer is `no`, the owner must state the corrected scope or required rerun. This request does not itself change N4 status.

## Recorded owner decision

The owner explicitly accepted this proposal with `OWNER_DECISION=ACCEPT_THIS_PROPOSAL`:

```text
OWNER_ACCEPTS_SCOPE03_TECHNICAL_RESULT=yes
OWNER_ACCEPTS_N4_EVIDENCE_CLASS=yes
OWNER_ACCEPTS_PROTOCOL_DEVIATION=yes
OWNER_ACCEPTS_NO_N4_RERUN=yes
```

The evidence provenance remains `OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED`; the SSH-over-`wlan0` deviation remains recorded.
