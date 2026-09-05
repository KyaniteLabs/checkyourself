# CheckYourself Coverage Matrix

A CheckYourself diagnostic is not allowed to stop after a few obvious issues. The reviewer must sweep every relevant production surface below and mark each one as one of:

- **Pass** — evidence shows the control exists and is credible.
- **Finding** — evidence shows a gap or risky implementation.
- **Unknown** — the reviewer cannot tell from available evidence. Unknowns in critical areas should become questions or temporary risks.
- **Not applicable** — the app genuinely does not use this surface.

The goal is maximum practical coverage, not fake certainty. If the AI cannot inspect enough of the project, it must say what it cannot verify.

| # | Surface | What to inspect | Typical findings |
|---:|---|---|---|
| 1 | Product purpose and users | What the app does, who can use it, who can be harmed | unclear risk model, missing admin/user distinction |
| 2 | Stack and architecture | framework, backend, database, host, integrations | unsupported assumptions, hidden serverless limits |
| 3 | Frontend UX and client safety | routing, forms, validation, state, accessibility, error states | client-only protection, broken loading/error flows |
| 4 | API and backend services | routes, input validation, business rules, uploads, webhooks | unsafe writes, missing validation, webhook trust bugs |
| 5 | Auth and permissions | login, sessions, roles, admin paths, server-side authorization | auth only in UI, role bypass, weak session handling |
| 6 | Data storage and migrations | schema, migrations, backups, constraints, seed data | destructive migrations, no constraints, no backup evidence |
| 7 | User/tenant isolation | tenant/user filters, RLS, cache keys, exports, logs | cross-user data leaks, tenant-blind cache keys |
| 8 | Secrets and environment config | env files, secret handling, public variables, config drift | exposed keys, missing env examples, prod/dev mismatch |
| 9 | Security and threat model | OWASP-style risks, injection, SSRF, XSS, CSRF, dependencies | untrusted input reaches dangerous sinks |
| 10 | Privacy and data governance | PII, retention, deletion, consent, logs, third-party sharing | collecting sensitive data without policy or deletion path |
| 11 | Tests and quality gates | unit/integration/e2e tests, dangerous paths, CI checks | no tests around auth, payments, writes, or data isolation |
| 12 | CI/CD and supply chain | lockfiles, dependency scans, SBOM/provenance, branch rules | unpinned deps, no scan, manual deploy risk |
| 13 | Hosting, deployment, rollback | environments, deploy process, preview/prod split, rollback | no rollback plan, manual env drift, prod secrets in dev |
| 14 | Cloud infrastructure/IaC | Terraform/Pulumi/cloud config, networking, storage permissions | public buckets, wide IAM, no infrastructure review |
| 15 | Performance, caching, rate limits | latency, load, indexes, cache correctness, abuse throttling | no rate limits, N+1 queries, cache leakage |
| 16 | Scaling and resilience | queues, retries, circuit breakers, graceful degradation | single point of failure, retry storms, no backpressure |
| 17 | Observability and incident response | logs, metrics, traces, error tracking, alerts, runbooks | no useful logs, no owner, no incident path |
| 18 | Availability and recovery | backups, restore tests, disaster recovery, data export | backups untested, no RTO/RPO, no recovery drill |
| 19 | AI/RAG/agent governance | prompts, tool permissions, evals, citations, refusal, sandboxing | hallucinated answers, unsafe tools, prompt injection, no evals |
| 20 | Learning needs | gaps that reveal what the builder should learn next | generic learning plan not tied to real findings |

## Completeness rule

The report must include a **Coverage Sweep** table. Every row above must be represented as Pass, Finding, Unknown, or Not applicable. The remediation backlog must include every row marked Finding and any high-impact Unknown that blocks confidence.

In prose, use **Not applicable**. In the coverage JSON written for the CLI, use
exactly these status values: `Pass`, `Finding`, `Unknown`, `NotApplicable`.
