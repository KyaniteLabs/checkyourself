---
id: prodhardening.hosting_deployment_release
name: hosting-deployment-release
version: 1.1.0
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
- Load the `wiggins-twelve-factor` skill (MIT) for the full Twelve-Factor App doctrine — stateless processes, config in env, build/release/run separation, disposability, dev/prod parity, logs as event streams.

## Enriched doctrine (from Twelve-Factor App)

Named decision rules that sharpen this capability. These rules **extend** — never override — the operating contract, work protocol, and verification gates above.

- **One codebase, many deploys.** A single VCS-tracked codebase fans out to many deploys (staging, prod) — never a forked prod codebase. Drift between deploys lives in config, not in copies of the code.
- **Immutable release artifact.** *Build* produces an artifact that never changes; *release* = artifact + config, itself immutable and permanently rollback-able; *run* executes it. Sharpening work-protocol item 2: the goal is promotable, rollback-able releases, not merely separated stages.
- **Same artifact, env-only divergence.** Config lives in the environment (Factor III), not the code. The identical build artifact promotes dev → staging → prod with zero code changes — env vars are the only contract between app and deploy environment. (Secret handling itself: `08-config-secrets-runtime`.)
- **Stateless, share-nothing processes are the precondition for safe deploy.** Any process can be killed or restarted; all state lives in backing stores. Without this, rolling/blue-green deploys and horizontal scaling cannot be safe — treat unmanaged statefulness as a deploy blocker.
- **Disposability: fast startup, graceful shutdown.** Robustness = start fast and exit cleanly on `SIGTERM` (finish in-flight work, release resources, then exit). This is the mechanism behind zero-downtime deploys, elastic scale, and safe restarts — the *why* behind work-protocol item 3's drain behavior.
- **Dev/prod parity — especially backing services.** Keep dev/staging/prod as similar as possible: same dependencies, same backing-service *kinds* (don't run SQLite in dev and Postgres in prod). Divergence is where deploy-time breakage hides.
- **Logs are event streams.** The app writes to stdout and never manages log files, rotation, or destinations; the deploy platform aggregates. This decouples the release artifact from log infrastructure.

*Source: The Twelve-Factor App (Adam Wiggins & contributors), MIT-licensed — derivative-safe to publish with attribution retained.*
## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
