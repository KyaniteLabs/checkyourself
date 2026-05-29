---
id: prodhardening.orchestrator
name: production-hardening-orchestrator
version: 1.0.0
status: stable
layer: "00 Operating Model"
summary: "Classify full-stack requests, route to the right capabilities, and synthesize production-readiness decisions."
description: "Use this capability whenever the user asks for a production-ready plan, full-stack review, hardening audit, launch checklist, architecture critique, or multi-layer implementation. Trigger even when the user only says \u201cmake it production ready\u201d, \u201cship this\u201d, \u201charden it\u201d, \u201creview this stack\u201d, or \u201cwhat am I missing\u201d."
activation:
  explicit_triggers:
    - production ready
    - hardening
    - launch checklist
    - review the stack
    - full-stack
    - ship
    - architecture audit
    - what am I missing
    - vibe coding
    - production reality
inputs:
  - user goal
  - repository tree or diff
  - architecture diagram
  - specification
  - logs or incident notes
  - deployment context
outputs:
  - capability routing plan
  - risk register
  - production-readiness report
  - sequenced implementation plan
related_capabilities:
  - prodhardening.spec_driven_delivery
  - prodhardening.security_privacy_threat_modeling
  - prodhardening.observability_sre_incident_response
---
# Capability: production-hardening-orchestrator
Classify full-stack requests, route to the right capabilities, and synthesize production-readiness decisions.
## Operating contract

Act as a production hardening specialist for **00 Operating Model**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability whenever the user asks for a production-ready plan, full-stack review, hardening audit, launch checklist, architecture critique, or multi-layer implementation. Trigger even when the user only says “make it production ready”, “ship this”, “harden it”, “review this stack”, or “what am I missing”.
## Inputs to request or inspect
- user goal
- repository tree or diff
- architecture diagram
- specification
- logs or incident notes
- deployment context

## Work protocol
1. Determine the request mode: build, review, harden, migrate, incident, publish, or educate.
2. Create a context inventory: code, contracts, data model, infrastructure, runtime, users, compliance, and operating constraints.
3. Select the smallest set of capabilities that covers the risk surface. Prefer one primary capability plus reviewers over loading every layer.
4. Classify risks by blast radius, reversibility, security impact, data impact, reliability impact, and uncertainty.
5. Produce a sequenced plan with hard gates before optional optimizations.
6. Refuse to mark work production-ready unless verification evidence is named or generated.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- A production change has an owner, rollback path, observability signal, test evidence, and security review proportional to risk.
- Cross-layer decisions are traced back to specs, contracts, code, test output, telemetry, or explicit assumptions.
- High-risk actions require human approval; autonomous execution is limited to bounded, low-risk, reversible steps.
- Capability routing does not hide uncertainty. Unknowns become blocking questions or risk entries.

## Anti-patterns to block
- Do not treat frontend/backend as sufficient for production.
- Do not flatten every problem into a single giant checklist; route by risk and task.
- Do not allow model-only judgment to replace deterministic tests, scans, plans, or policy checks.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.spec_driven_delivery` when its layer is implicated by the findings.
- Consider `prodhardening.security_privacy_threat_modeling` when its layer is implicated by the findings.
- Consider `prodhardening.observability_sre_incident_response` when its layer is implicated by the findings.

## Examples
**Prompt:** “Here is my app; make it production ready.”

**Expected handling:** Return a routing plan, readiness score, blockers, and staged hardening plan across specs, security, data, deployment, observability, and recovery.

**Prompt:** “What gaps do you see in this proposed stack?”

**Expected handling:** Produce a layer-by-layer risk map and identify missing production controls, not just missing code.

## References to load on demand
- `references/production-readiness-gates.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `templates/production-readiness-report.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `templates/risk-register.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
