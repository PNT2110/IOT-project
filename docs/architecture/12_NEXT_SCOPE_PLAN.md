# Next scope plan

The next coding scope is **PC Web + API contract completion**, followed by a
read-only Pi edge acceptance pass; firmware flashing remains outside the
current verified boundary.

1. Decide and document the role vocabulary mapping: `OWNER`, `ADMIN`,
   `OPERATOR` and public/guest user behavior.
2. Add contract tests for public zones, internal zone CRUD, account review,
   role review and simulated flight approval.
3. Implement the Web authentication state machine against `frontend/src/api.ts`
   (registration, terms, email OTP, TOTP, logout and session refresh).
4. Add the public map renderer and GeoJSON editor only for authorized roles.
5. Add role-specific approval tabs with server-enforced permissions.
6. Keep actuator and firmware-write endpoints disabled until the PC contract,
   device identity and bench safety evidence are green.

Completion of this scope means the PC product is internally coherent; it does
not mean the system is an official government service or flight authority.
