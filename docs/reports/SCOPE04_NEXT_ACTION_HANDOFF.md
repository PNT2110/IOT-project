# SCOPE-04 Next Action Handoff

This is the pre-reconciliation handoff snapshot. The current handoff is in
`SCOPE04_NEXT_ACTION_HANDOFF_CURRENT.md`.

Current handoff state: `BOUNDED_MANUAL_SMOKE_COMPLETE__SYSTEMD_AUTH_BOOTSTRAP_PENDING`.

Completed in this turn:

- repository implementation and versioned contract;
- PC mock tests and full SCOPE-01/02/03/04 regression;
- security, resource, implementation, and deviation reports;
- live deployment approval packet with explicit stop conditions.
- Pi preflight, isolated deployment, HTTPS transport decision, transient
  `/dev/video0` frame smoke, typed offline-state smoke, and resource sample.

Owner must decide whether to approve persistent local-account/bootstrap design
and unattended systemd operation. External F450 browser testing also requires
a real client and a certificate-trust decision. Do not send credentials in
chat or reports.

Until then:

```text
PI_SSH_OR_CONSOLE=USED_FOR_ACCEPTED_BOUNDED_DEPLOYMENT
PI_MUTATION=BOUNDED_SCOPE04_ONLY
NETWORK_CHANGE=NOT_AUTHORIZED_AND_NOT_RUN
CAMERA_CAPTURE=TRANSIENT_SINGLE_FRAME_PASS
SYSTEMD_AUTOSTART=NOT_RUN
F450_EXTERNAL_BROWSER=NOT_RUN
SCOPE05_PLUS=NOT_AUTHORIZED
```
