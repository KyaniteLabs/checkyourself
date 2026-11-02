---
id: prodhardening.security_privacy_threat_modeling
name: security-privacy-threat-modeling
version: 1.1.0
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
# security-privacy-threat-modeling
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
- [OWASP Top 10:2025](https://owasp.org/Top10/2025/) — the canonical root-cause threat-categorization reference (© OWASP Foundation, CC BY-SA 4.0).

## Enriched doctrine (from OWASP Top 10:2025)

The OWASP Top 10:2025 as a named threat-categorization checklist — map every finding to these root-cause categories. These rules **extend** — never override — the operating contract, work protocol, and verification gates above. (2025 changes called out: A03 Supply Chain and A10 Exceptional Conditions are new; SSRF is folded into A01.)

- **A01 Broken Access Control (#1).** Enforce authorization on every request, deny by default, validate server-side. SSRF is now folded here — treat server-side request targets as a privilege boundary. The most prevalent category.
- **A02 Security Misconfiguration (#2, up from #5).** Secure defaults, no default credentials, disable unused features/ports, repeatable hardening. App behavior is increasingly config-driven, so misconfiguration is rising.
- **A03 Software Supply Chain Failures (#3, NEW).** Verify integrity across dependencies, build systems, and distribution infrastructure: pinned dependencies, signed artifacts, SBOM. Lowest frequency but highest average exploit + impact. → hands off to `10-ci-cd-supply-chain`.
- **A04 Cryptographic Failures (#4).** Encrypt sensitive data in transit and at rest; use vetted algorithms and key management; never roll your own crypto. Leads to sensitive-data exposure or system compromise.
- **A05 Injection (#5).** Separate data from commands: parameterized queries, output encoding, prepared statements. Spans XSS (high-frequency / low-impact) to SQLi (low-frequency / high-impact); the most CVEs of any category.
- **A06 Insecure Design (#6).** Threat-model abuse cases in at design time; security is an architecture property, not a bolted-on control. Catch it at shaping, not in review.
- **A07 Authentication Failures (#7).** Use standardized auth frameworks; enforce MFA, session invalidation, credential rotation, replay protection. Framework adoption is measurably reducing occurrences.
- **A08 Software / Data Integrity Failures (#8).** Maintain trust boundaries and verify the integrity of code and data artifacts (signed updates, verified CI trust) at a level below the supply chain.
- **A09 Security Logging & Alerting Failures (#9).** Logging without alerting has minimal value — alerts are what induce action. Log security-relevant events AND raise actionable alerts. → hands off to `15-observability-sre-incident-response`.
- **A10 Mishandling of Exceptional Conditions (#10, NEW).** Fail secure (closed), not open. Handle exceptions without leaking internals or granting access; watch logic errors and fail-open paths.

*Source: OWASP Top 10:2025, © OWASP Foundation, CC BY-SA 4.0 (attribution + share-alike). Independent Kyanite Labs synthesis — names the root-cause categories and restates the guidance; does not reproduce the document.*
## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
