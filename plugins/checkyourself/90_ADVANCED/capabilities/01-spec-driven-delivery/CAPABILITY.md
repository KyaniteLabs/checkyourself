---
id: prodhardening.spec_driven_delivery
name: spec-driven-delivery
version: 1.0.0
status: stable
layer: "01 Product Intent & Contracts"
summary: "Convert ambiguous product intent into machine-checkable specs, acceptance criteria, and change plans."
description: "Use this capability when defining, refining, or reviewing a feature before implementation. Trigger on requirements, user stories, acceptance criteria, OpenAPI, AsyncAPI, JSON Schema, contracts, ADRs, RFCs, roadmap items, or \u201cturn this idea into buildable work\u201d."
activation:
  explicit_triggers:
    - requirements
    - user story
    - acceptance criteria
    - OpenAPI
    - AsyncAPI
    - JSON Schema
    - ADR
    - RFC
    - spec
    - contract
    - roadmap
    - feature plan
inputs:
  - product idea
  - research note
  - customer feedback
  - existing APIs
  - schema definitions
  - constraints
outputs:
  - buildable specification
  - acceptance criteria
  - API/data contracts
  - ADR
  - test plan seed
  - risk assumptions
related_capabilities:
  - prodhardening.api_backend_services
  - prodhardening.testing_quality_engineering
  - prodhardening.orchestrator
---
# Capability: spec-driven-delivery
Convert ambiguous product intent into machine-checkable specs, acceptance criteria, and change plans.
## Operating contract

Act as a production hardening specialist for **01 Product Intent & Contracts**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability when defining, refining, or reviewing a feature before implementation. Trigger on requirements, user stories, acceptance criteria, OpenAPI, AsyncAPI, JSON Schema, contracts, ADRs, RFCs, roadmap items, or “turn this idea into buildable work”.
## Inputs to request or inspect
- product idea
- research note
- customer feedback
- existing APIs
- schema definitions
- constraints

## Work protocol
1. Separate intent from implementation. Capture actors, jobs, constraints, non-goals, and success measures first.
2. Write contracts before code: request/response shapes, events, permissions, data lifecycle, observability signals, and failure modes.
3. Define acceptance criteria as verifiable statements, not vague outcomes.
4. Identify product, technical, security, privacy, and operational assumptions. Mark blocking assumptions explicitly.
5. Create a minimum viable production slice: the smallest implementation that includes auth, tests, telemetry, rollback, and docs.
6. Update specs when requirements change; regenerate or refactor code from the source of truth rather than letting code drift silently.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Every feature has a clear owner, measurable acceptance criteria, and a non-goal section.
- Every external boundary has a schema or contract and compatibility strategy.
- Every production behavior names expected failure modes and user-visible fallback behavior.
- Human review checkpoints exist for priorities, specs, and intent-to-ship decisions.

## Anti-patterns to block
- Do not start with framework scaffolding when the contract is unknown.
- Do not let generated code become the only specification.
- Do not accept “works locally” as an acceptance criterion.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.api_backend_services` when its layer is implicated by the findings.
- Consider `prodhardening.testing_quality_engineering` when its layer is implicated by the findings.
- Consider `prodhardening.orchestrator` when its layer is implicated by the findings.

## Examples
**Prompt:** “Turn this feature idea into an implementation plan.”

**Expected handling:** Return a spec, acceptance tests, API/data contracts, risk assumptions, and sequencing.

**Prompt:** “Review this OpenAPI file before implementation.”

**Expected handling:** Check completeness, consistency, auth, error model, pagination, idempotency, and testability.

## References to load on demand
- `../../references/spec-driven-delivery.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `../../templates/adr.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `../../templates/spec-template.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
