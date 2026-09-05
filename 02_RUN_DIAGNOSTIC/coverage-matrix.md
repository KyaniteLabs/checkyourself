# CheckYourself Coverage Matrix

Sweep every relevant surface. Mark each `Pass`, `Finding`, `Unknown`, or `Not applicable`:

- **Pass:** verifier-captured, non-empty receipt with matching content hashes and provenance backs assertions.
- **Finding:** evidence shows a gap or risky implementation.
- **Unknown:** evidence cannot establish state; critical unknowns become questions or temporary risks.
- **Not applicable:** the app lacks the surface and a verifier-captured delegation receipt shows responsibility.

| # | Surface | Inspect | Typical findings |
|---:|---|---|---|
| 1 | Product purpose and users | purpose/users/harm | unclear risk model; admin/user gap |
| 2 | Stack and architecture | framework/backend/DB/host/integrations | unsupported assumptions; serverless limits |
| 3 | Frontend UX and client safety | routes/forms/validation/state/a11y/errors | client-only protection; broken states |
| 4 | API and backend services | routes/validation/rules/uploads/webhooks | unsafe writes; validation; webhook trust |
| 5 | Auth and permissions | login/sessions/roles/admin/server auth | UI-only auth; role bypass; weak sessions |
| 6 | Data storage and migrations | schema/migrations/backups/constraints/seeds | destructive migration; missing constraints/backup |
| 7 | User/tenant isolation | filters/RLS/cache keys/exports/logs | cross-user leak; tenant-blind cache |
| 8 | Secrets and environment config | env/secrets/public vars/drift | exposed key; missing example; prod/dev mismatch |
| 9 | Security and threat model | injection/SSRF/XSS/CSRF/dependencies | untrusted input reaches dangerous sink |
| 10 | Privacy and data governance | PII/retention/deletion/consent/logs/sharing | sensitive collection without policy/deletion |
| 11 | Tests and quality gates | unit/integration/e2e/dangerous paths/CI | missing auth/payment/write/isolation tests |
| 12 | CI/CD and supply chain | lockfiles/scans/SBOM/provenance/branch rules | unpinned deps; no scan; manual deploy |
| 13 | Hosting, deployment, rollback | envs/deploy/preview/prod/rollback | env drift; no rollback; prod secrets in dev |
| 14 | Cloud infrastructure/IaC | Terraform/Pulumi/cloud/network/storage/IAM | public bucket; wide IAM; no review |
| 15 | Performance, caching, rate limits | latency/load/indexes/cache/throttling | no limits; N+1; cache leakage |
| 16 | Scaling and resilience | queues/retries/breakers/degradation | single point; retry storm; no backpressure |
| 17 | Observability and incident response | logs/metrics/traces/alerts/runbooks | no useful logs, owner, or incident path |
| 18 | Availability and recovery | backups/restore/DR/export | untested backup; no RTO/RPO/drill |
| 19 | AI/RAG/agent governance | prompts/tools/evals/citations/refusal/sandbox | hallucination; unsafe tool; injection; no eval |
| 20 | Learning needs | gaps exposed by findings | generic plan not tied to findings |

## Completeness rule

Report must include **Coverage Sweep** with all rows. Backlog includes every
Finding and blocking high-impact Unknown.
Use **Not applicable** in prose; coverage JSON uses exactly `Pass`, `Finding`,
`Unknown`, or `NotApplicable`.
