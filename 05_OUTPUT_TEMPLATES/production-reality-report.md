# Production Reality Report

## 1. Executive Summary


## 2. What this app appears to do


## 3. Detected stack

| Area | Detected technology | Evidence | Confidence |
|---|---|---|---|
| Frontend |  |  |  |
| Backend |  |  |  |
| Database |  |  |  |
| Auth |  |  |  |
| Hosting/deployment |  |  |  |
| Testing |  |  |  |
| AI/RAG/agents |  |  |  |

## 4. Unknowns and assumptions

| Unknown/assumption | Why it matters | How to resolve | Blocks score? |
|---|---|---|---|

### Public repository scope confirmation, if applicable

| Owner namespace | Repository count | Fork policy | Verification time | Live evidence checked | Not included |
|---|---:|---|---|---|---|

## 5. Production Reality Score

**Score:** __ / 100
**Confidence:** High / Medium / Low

### Score breakdown

| Category | Weight | Awarded | Evidence | What would improve it |
|---|---:|---:|---|---|
| Data, privacy, and tenant/user isolation | 18 |  |  |  |
| Auth, permissions, and session safety | 14 |  |  |  |
| Secrets, environment, and runtime config | 10 |  |  |  |
| API, validation, uploads, and business logic | 10 |  |  |  |
| Testing and quality gates | 10 |  |  |  |
| Deployment, release, rollback, and CI/CD | 8 |  |  |  |
| Observability, logs, errors, and incident response | 8 |  |  |  |
| Performance, scaling, caching, and rate limits | 8 |  |  |  |
| Frontend UX, accessibility, and client safety | 8 |  |  |  |
| AI/RAG/agent governance, if applicable | 6 |  |  |  |

### Score cap applied

- [ ] P0 cap at 49
- [ ] P1 cap at 74
- [ ] Missing evidence cap at 84
- [ ] Missing key launch-gate evidence cap at 90
- [ ] No cap

## 6. Coverage Sweep

Every relevant production surface must be represented here. Do not stop after a few obvious issues.

| # | Surface | Status: Pass / Finding / Unknown / N/A | Evidence or reason | Related finding IDs |
|---:|---|---|---|---|
| 1 | Product purpose and users |  |  |  |
| 2 | Stack and architecture |  |  |  |
| 3 | Frontend UX and client safety |  |  |  |
| 4 | API and backend services |  |  |  |
| 5 | Auth and permissions |  |  |  |
| 6 | Data storage and migrations |  |  |  |
| 7 | User/tenant isolation |  |  |  |
| 8 | Secrets and environment config |  |  |  |
| 9 | Security and threat model |  |  |  |
| 10 | Privacy and data governance |  |  |  |
| 11 | Tests and quality gates |  |  |  |
| 12 | CI/CD and supply chain |  |  |  |
| 13 | Hosting, deployment, rollback |  |  |  |
| 14 | Cloud infrastructure/IaC |  |  |  |
| 15 | Performance, caching, rate limits |  |  |  |
| 16 | Scaling and resilience |  |  |  |
| 17 | Observability and incident response |  |  |  |
| 18 | Availability and recovery |  |  |  |
| 19 | AI/RAG/agent governance |  |  |  |
| 20 | Learning needs |  |  |  |

## 7. P0 findings — do not ship

| ID | Finding | Plain-English risk | Evidence | Recommended fix |
|---|---|---|---|---|

## 8. P1 findings — serious before launch

| ID | Finding | Plain-English risk | Evidence | Recommended fix |
|---|---|---|---|---|

## 9. P2 findings — important hardening gaps

| ID | Finding | Plain-English risk | Evidence | Recommended fix |
|---|---|---|---|---|

## 10. P3 findings — improvements

| ID | Finding | Why it helps | Evidence | Suggested timing |
|---|---|---|---|---|

## 11. Evidence table

| Evidence | File/location | Supports finding | Confidence |
|---|---|---|---|

## 12. Complete ranked remediation backlog

List every finding that needs remediation. The first approval batch is only the starting point, not the full scope.

| Order | Finding ID | Severity | Fix summary | Why this order | Approval needed | Verification | Rollback | Learning value | Status |
|---:|---|---|---|---|---|---|---|---|---|

## 13. Safest first approval batch

Select the smallest safe batch to approve first from the complete backlog. This may be one fix, several related fixes, or all P0 fixes if they are tightly coupled. Do not present this as the whole project scope.

### Fix card

- Finding ID:
- Why this comes first:
- Plain-English explanation:
- Technical change:
- Files likely touched:
- Verification:
- Rollback:
- Learning value:
- Approval question:

## 14. Full remediation path

Explain how to continue after the first approved batch.

| Wave | Included findings | Goal | Exit criteria |
|---|---|---|---|
| Wave 1 |  | Remove do-not-ship blockers |  |
| Wave 2 |  | Remove serious launch risks |  |
| Wave 3 |  | Complete important hardening |  |
| Wave 4 |  | Cleanup, polish, and learning |  |

## 15. What can wait, and why

This section is not for hiding issues. Anything deferred must still appear in the backlog.

| Deferred item | Why it can wait | Trigger that makes it urgent |
|---|---|---|

## 16. Questions that would change this diagnosis


## 17. Learning-plan seeds

| Finding | Concept to learn | Why it matters now | Suggested exercise |
|---|---|---|---|

## 18. Optional dashboard offer

The dashboard is optional. Ask the user before generating it.

Suggested language:

```text
I can also generate a visual CheckYourself HTML/CSS dashboard from this report. It is optional and may use extra tokens. Do you want the dashboard?
```

## 19. Optional dashboard handoff

Dashboard generated? Yes / No

Default: No. Offer the dashboard only after the report is complete. Generate it only when the user explicitly asks, with wording such as `dashboard yes` or `dashboard inline`.

If generated, use `10_DASHBOARD/CONTEXT.md` and include the complete remediation backlog. Do not re-run the audit just to build the dashboard.

If the user declines HTML/CSS, provide the inline Markdown dashboard fallback with:

- project name;
- score before/after, if applicable;
- ship status;
- counts by severity and status;
- coverage summary;
- complete findings table;
- complete remediation backlog;
- current approval batch;
- learning-plan highlights.

Keep dashboard evidence concise. Link or reference files by path instead of pasting raw file content.
