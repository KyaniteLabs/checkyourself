# Risk Taxonomy

## P0 — Do not ship

Use P0 for issues that could reasonably cause:

- cross-user or cross-tenant data leaks;
- exposed secrets or credentials;
- broken authentication or authorization;
- destructive unauthenticated actions;
- payment or financial harm;
- sensitive data exposure;
- production outage with no rollback/recovery path;
- unsafe AI behavior with high user harm.

## P1 — Serious before launch

Use P1 for issues that are likely to cause harm under real use, even if not immediately catastrophic.

Examples:

- no server-side validation on important writes;
- no rate limits on abuse-prone endpoints;
- no error monitoring for a public launch;
- missing tests around core business logic;
- risky deployment process with no documented rollback.

## P2 — Important hardening gap

Use P2 for issues that should be fixed soon, but do not block every launch.

Examples:

- incomplete accessibility pass;
- unmeasured performance risk;
- limited structured logging;
- test coverage missing for secondary flows.

## P3 — Improvement

Use P3 for cleanup, maintainability, UX polish, and learning opportunities.
