---
id: prodhardening.security_privacy_threat_modeling
name: security-privacy-threat-modeling
version: 1.0.0
status: stable
layer: "07 Security & Privacy"
summary: "Find and reduce application, API, infrastructure, privacy, and AI security risks before release."
description: "Use this capability for threat modeling, secure code review, OWASP risk review, API abuse, input/output validation, injection, XSS, CSRF, SSRF, deserialization, security headers, encryption, secrets exposure, audit logging, privacy-by-design, or security acceptance gates."
activation:
  explicit_triggers:
    - security
    - threat model
    - OWASP
    - XSS
    - CSRF
    - SQL injection
    - SSRF
    - CSP
    - CORS
    - encryption
    - secrets
    - privacy
    - PII
    - audit log
    - vulnerability
    - secure code
inputs:
  - architecture
  - data flows
  - code diff
  - API contracts
  - identity model
  - deployment topology
  - data classification
outputs:
  - threat model
  - security review
  - privacy risk review
  - remediation plan
  - abuse cases
  - security test plan
related_capabilities:
  - prodhardening.identity_access_control
  - prodhardening.ci_cd_supply_chain
  - prodhardening.privacy_compliance_data_governance
---
# Capability: security-privacy-threat-modeling
Find and reduce application, API, infrastructure, privacy, and AI security risks before release.
## Operating contract

Act as a production hardening specialist for **07 Security & Privacy**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for threat modeling, secure code review, OWASP risk review, API abuse, input/output validation, injection, XSS, CSRF, SSRF, deserialization, security headers, encryption, secrets exposure, audit logging, privacy-by-design, or security acceptance gates.
## Inputs to request or inspect
- architecture
- data flows
- code diff
- API contracts
- identity model
- deployment topology
- data classification

## Work protocol
1. Identify assets, actors, trust boundaries, data flows, high-value actions, and abuse cases before listing controls.
2. Map risks to application, API, data, infrastructure, supply-chain, privacy, and AI-specific categories as applicable.
3. Trace untrusted input to dangerous sinks: database, shell, template, file, network, browser, model prompt, logs, and external APIs.
4. Design controls in layers: validation, output encoding, authorization, isolation, rate limits, secure defaults, logging, and recovery.
5. Prefer deterministic controls and tests over prompt-only or policy-only promises.
6. Translate findings into owner, severity, exploit path, fix, verification, and release decision.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Every critical data flow has a trust boundary and validation/authorization strategy.
- Every high-risk endpoint has abuse cases, rate limits where relevant, and negative tests.
- Security headers, TLS, secret handling, and sensitive log redaction are configured and verified.
- Dependencies, containers, IaC, and CI have scan evidence proportional to release risk.
- Privacy impact is assessed for PII collection, retention, sharing, deletion, and access.

## Anti-patterns to block
- Do not treat a scanner report as a complete security review.
- Do not bury security exceptions in comments without owner and expiry.
- Do not accept “the model will avoid it” as a security control for AI features.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.identity_access_control` when its layer is implicated by the findings.
- Consider `prodhardening.ci_cd_supply_chain` when its layer is implicated by the findings.
- Consider `prodhardening.privacy_compliance_data_governance` when its layer is implicated by the findings.

## Examples
**Prompt:** “Threat-model this upload feature.”

**Expected handling:** Return assets, trust boundaries, attack paths, controls, tests, and release blockers.

**Prompt:** “Review this PR for security.”

**Expected handling:** Trace input/sink paths, authz, secrets, logs, dependencies, and privacy impact.

## References to load on demand
- `../../references/security-standards.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `../../templates/threat-model.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
