---
id: prodhardening.config_secrets_runtime
name: config-secrets-runtime
version: 1.0.0
status: stable
layer: "08 Configuration, Secrets & Runtime"
summary: "Harden environment configuration, secret management, feature flags, runtime policy, and safe defaults."
description: "Use this capability for environment variables, config schemas, secrets, key rotation, feature flags, runtime toggles, service discovery, dotenv cleanup, secret scanning, config drift, and environment parity. Trigger on env, config, secret, API key, credentials, feature flag, toggle, runtime, staging, production config, or rotation."
activation:
  explicit_triggers:
    - env
    - environment variable
    - config
    - secret
    - API key
    - credentials
    - feature flag
    - toggle
    - runtime
    - rotation
    - staging
    - dotenv
    - config drift
inputs:
  - config files
  - environment list
  - secret inventory
  - deployment manifests
  - runtime defaults
  - feature flags
outputs:
  - configuration contract
  - secret inventory
  - rotation plan
  - runtime validation checks
  - feature-flag governance
related_capabilities:
  - prodhardening.hosting_deployment_release
  - prodhardening.cloud_infrastructure_iac
  - prodhardening.security_privacy_threat_modeling
---
# config-secrets-runtime
Harden environment configuration, secret management, feature flags, runtime policy, and safe defaults.
## Operating contract

Act as a production hardening specialist for **08 Configuration, Secrets & Runtime**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for environment variables, config schemas, secrets, key rotation, feature flags, runtime toggles, service discovery, dotenv cleanup, secret scanning, config drift, and environment parity. Trigger on env, config, secret, API key, credentials, feature flag, toggle, runtime, staging, production config, or rotation.
## Inputs to request or inspect
- config files
- environment list
- secret inventory
- deployment manifests
- runtime defaults
- feature flags

## Work protocol
1. Inventory all configuration values and classify them as public config, sensitive secret, operational limit, feature flag, or deployment constant.
2. Define typed config schemas with startup validation and safe failure behavior.
3. Move secrets to managed storage or platform secrets. Remove secrets from repos, logs, images, browser bundles, and examples.
4. Design rotation, revocation, and incident response for every credential with production access.
5. Treat feature flags as production code: owners, expiry dates, default states, telemetry, and kill-switch behavior.
6. Verify environment parity while allowing deliberate differences for scale, regions, domains, and credentials.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Application fails closed on missing or invalid critical configuration.
- No production secret is stored in source control, image layers, frontend bundles, or plain-text logs.
- Every secret has owner, scope, storage location, rotation cadence, and break-glass procedure.
- Feature flags have owners, default state, rollback behavior, and cleanup plan.
- Configuration drift is detectable before deploy or during startup.

## Anti-patterns to block
- Do not rely on comments or README notes for required env variables; validate at runtime.
- Do not use one shared admin credential across services and environments.
- Do not leave expired feature flags as permanent hidden branches.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.hosting_deployment_release` when its layer is implicated by the findings.
- Consider `prodhardening.cloud_infrastructure_iac` when its layer is implicated by the findings.
- Consider `prodhardening.security_privacy_threat_modeling` when its layer is implicated by the findings.

## Examples
**Prompt:** “Clean up the env var setup.”

**Expected handling:** Return typed config schema, required/optional list, secret storage plan, and startup validation.

**Prompt:** “Add a feature flag for checkout.”

**Expected handling:** Define owner, rollout, kill switch, telemetry, default states, and removal plan.

## References to load on demand
- `../../references/config-secrets-runtime.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `../../templates/risk-register.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
