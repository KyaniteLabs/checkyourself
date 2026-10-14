# Production Readiness Gates

Use these gates as release blockers or exception-driven review items.

## Universal release gates

| Gate | Evidence |
|---|---|
| Spec and acceptance criteria | Approved spec, ADR, issue, or clear written intent. |
| Tests | Unit/integration/contract/e2e/security/performance coverage proportional to risk. |
| Security | Threat model or review, dependency scan, secret scan, authz negative tests where applicable. |
| Data | Migration plan, backup/restore behavior, retention/deletion, tenant isolation where applicable. |
| Deployment | Reproducible build, deployment plan, smoke tests, rollback/roll-forward path. |
| Observability | Logs, metrics, traces, dashboards, alerts, runbook, redaction. |
| Recovery | SLO/RTO/RPO fit, backup restore evidence, incident escalation path. |
| Ownership | Code owner, service owner, on-call/support path, documentation. |

## Risk scoring

Score each proposed action on a 1–5 scale:

- **Blast radius:** users/data/systems affected.
- **Reversibility:** how easy it is to roll back.
- **Security/privacy impact:** credentials, PII, authorization, tenant isolation.
- **Operational complexity:** number of systems and humans involved.
- **Uncertainty:** missing context or unverified assumptions.

High total risk requires staged rollout, explicit approval, and stronger evidence.
