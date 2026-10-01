# Security review before public deployment

## Current positive controls

- Passwords are handled by the server security module rather than the Web UI.
- Authenticated workflows have server-side role checks, version checks and
  audit/history records.
- Synthetic flight results are explicitly labelled as not a flight permit.
- The deployed API binds loopback behind a tunnel; the SQLite file is not a
  public listener.

## Blocking gaps

1. The quick tunnel is temporary and unauthenticated at the edge.
2. There is no production reverse proxy/named tunnel, rate limiting or abuse
   policy documented for a public service.
3. Fake mail is a development adapter; OTP delivery is not production-ready.
4. The frontend does not yet implement the full authenticated user/admin UX.
5. Device identity and Pi credentials are not implemented in the active tree.
6. Backup/restore, retention and incident response are not operationalized.
7. The local workspace has no Git history, so release review/rollback is weak.

## Required gate

Do not label the service as a real Ministry system or accept real flight
requests until HTTPS, named-domain ownership, real mail, secret storage,
rate limiting, authorization tests, logging redaction, backups and an
approved external-authority adapter have all been reviewed. Hardware arm and
motor commands remain disabled throughout the current research scope.
