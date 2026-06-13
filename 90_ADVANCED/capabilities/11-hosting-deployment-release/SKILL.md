---
id: prodhardening.hosting_deployment_release
name: hosting-deployment-release
version: 1.0.0
status: stable
layer: "11 Hosting & Deployment"
summary: "Choose hosting and deployment patterns, design safe releases, configure health checks, and plan rollbacks."
description: "Use this capability for hosting decisions, platform selection, container deployment, serverless deployment, domains, DNS, TLS, staging/production environments, blue-green, canary, rolling deploys, migrations during deploy, health checks, smoke tests, and rollback plans."
activation:
  explicit_triggers:
    - hosting
    - deploy
    - deployment
    - serverless
    - container
    - Docker
    - domain
    - DNS
    - TLS
    - staging
    - production
    - blue-green
    - canary
    - rolling
    - health check
    - smoke test
    - rollback
inputs:
  - application architecture
  - runtime requirements
  - traffic profile
  - deployment scripts
  - environment config
  - migration plan
outputs:
  - deployment architecture
  - release plan
  - health check design
  - smoke test checklist
  - rollback runbook
related_capabilities:
  - prodhardening.config_secrets_runtime
  - prodhardening.cloud_infrastructure_iac
  - prodhardening.availability_recovery_continuity
---
# hosting-deployment-release
Choose hosting and deployment patterns, design safe releases, configure health checks, and plan rollbacks.
## Operating contract

Act as a production hardening specialist for **11 Hosting & Deployment**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for hosting decisions, platform selection, container deployment, serverless deployment, domains, DNS, TLS, staging/production environments, blue-green, canary, rolling deploys, migrations during deploy, health checks, smoke tests, and rollback plans.
## Inputs to request or inspect
- application architecture
- runtime requirements
- traffic profile
- deployment scripts
- environment config
- migration plan

## Work protocol
1. Choose hosting based on operational complexity, latency, scaling, data locality, team skills, cost, compliance, and rollback needs.
2. Separate build, release, and run stages so artifacts can be promoted and rolled back safely.
3. Design deploys around health checks, readiness, liveness, drain behavior, migrations, and dependent service availability.
4. Use progressive delivery for risky changes: canary, blue-green, feature flags, staged traffic, and automatic rollback signals.
5. Define smoke tests that prove the deployed artifact, configuration, database compatibility, and critical external integrations.
6. Document rollback versus roll-forward decisions before launch.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Every deploy has preflight checks, smoke tests, health signals, and rollback/roll-forward path.
- Database migrations are compatible with current and next application versions where zero downtime is required.
- TLS, domains, redirects, CORS origins, and environment variables are verified per environment.
- Deploy credentials are scoped and separated from build/test credentials.
- Release notes identify user impact, operational impact, and support/debug instructions.

## Anti-patterns to block
- Do not combine irreversible data changes with untested application deploys.
- Do not use a single health endpoint that returns healthy while dependencies are broken for critical paths.
- Do not skip rollback planning because the change “looks small”.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.config_secrets_runtime` when its layer is implicated by the findings.
- Consider `prodhardening.cloud_infrastructure_iac` when its layer is implicated by the findings.
- Consider `prodhardening.availability_recovery_continuity` when its layer is implicated by the findings.

## Examples
**Prompt:** “Deploy this app to production.”

**Expected handling:** Return platform decision, env/config plan, CI/CD path, health checks, smoke tests, migration strategy, and rollback.

**Prompt:** “Can we use canary deploys here?”

**Expected handling:** Evaluate traffic routing, telemetry, blast radius, automatic rollback, and state compatibility.

## References to load on demand
- `../../references/deployment-release.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `../../templates/release-checklist.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
