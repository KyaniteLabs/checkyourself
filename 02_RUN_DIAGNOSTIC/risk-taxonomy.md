# Risk Taxonomy

| Severity | Use for |
|---|---|
| **P0 — Do not ship** | Issues that could reasonably cause cross-user/cross-tenant leaks; exposed secrets/credentials; broken auth/authorization; destructive unauthenticated actions; payment/financial harm; sensitive-data exposure; outage without rollback/recovery; or unsafe AI with high user harm. |
| **P1 — Serious before launch** | Likely real-use harm that is not immediately catastrophic: no server-side validation on important writes; no rate limits on abuse-prone endpoints; no public-launch error monitoring; missing core-business tests; or risky deployment without documented rollback. |
| **P2 — Important hardening gap** | Fix soon, but not a universal launch blocker: incomplete accessibility; unmeasured performance; limited structured logging; or missing secondary-flow tests. |
| **P3 — Improvement** | Cleanup, maintainability, UX polish, and learning opportunities. |
