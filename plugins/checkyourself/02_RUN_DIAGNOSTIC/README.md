# 02 - Run Diagnostic

The diagnostic is read-only. Its job is to create a Production Reality Report:
the honest pre-launch reality check before production does the grading.

## Diagnostic phases

1. **Map the app** - purpose, users, data, stack, deployment path.
2. **Map risk surfaces** - auth, data, API, frontend, deployment, observability, performance, AI.
3. **Collect evidence** - files, configs, tests, docs, observed patterns.
4. **Rank findings** - P0/P1/P2/P3.
5. **Score readiness** - evidence-based, with caps for severe unresolved risks.
6. **Create the complete findings register** - no artificial cap on findings; include every supported issue.
7. **Create the complete remediation backlog** - every finding gets a proposed fix, verification method, rollback note, and status.
8. **Select the safest first approval batch** - a small starting batch, never the full scope.
9. **Generate learning-plan seeds** - concepts implied by the findings and fixes.


## Completeness rule

Do **not** stop after the first few issues. The diagnostic should cover every relevant production risk surface and record all supported findings.

The first approval batch exists to keep remediation safe and understandable. It must never be treated as the entire set of required fixes.

Each finding should end in one of these states:

- `open` — found but not fixed yet;
- `proposed` — fix card exists and awaits approval;
- `approved` — user approved the fix;
- `fixed` — change made and verified;
- `accepted-risk` — user consciously chose not to fix now;
- `deferred` — user schedules it for later with a reason/date;
- `not-applicable` — later evidence showed it does not apply;
- `suppressed` — reviewed false positive scoped in `.checkyourself.yml`.

## Mandatory categories

The AI should inspect or ask about:

- app purpose and user types;
- stack and deployment;
- auth, roles, and permissions;
- data isolation and privacy;
- secrets and environment variables;
- API routes, forms, validation, uploads;
- tests and quality gates;
- CI/CD and release process;
- rollback plan;
- logs, errors, monitoring, alerting;
- performance, scaling, caching, rate limits;
- AI/RAG/agent features, if present;
- legal/compliance concerns, if relevant.

## Output format

Use [`../05_OUTPUT_TEMPLATES/production-reality-report.md`](../05_OUTPUT_TEMPLATES/production-reality-report.md).

## Completeness versus token efficiency

A complete audit does not mean an enormous response.

Required:

- every relevant surface appears in the coverage sweep;
- every supported finding appears in the findings register;
- every finding and blocking unknown appears in the remediation backlog.

Token-efficient default:

- keep P2/P3 rows compact;
- expand only P0/P1 and the next approval batch;
- avoid raw file dumps;
- generate the HTML dashboard only after the user opts in.


## Optional dashboard

Do not produce a dashboard by default.

If the user requests one, use the canonical dashboard guidance in
[`../10_DASHBOARD/README.md`](../10_DASHBOARD/README.md).

The dashboard must be derived from the complete report and backlog. It should not replace them.

The dashboard must visualize the complete backlog, not only the first approval batch.

## Context control

Use the coverage matrix to keep the audit complete. Use compact rows and finding IDs to keep the output manageable. Load advanced references only when a risk surface needs deeper treatment.
