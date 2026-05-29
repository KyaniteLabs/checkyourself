---
id: prodhardening.api_backend_services
name: api-backend-services
version: 1.0.0
status: stable
layer: "03 APIs & Backend Logic"
summary: "Design and harden APIs, service boundaries, validation, business logic, and integration contracts."
description: "Use this capability for REST, GraphQL, gRPC, webhooks, background jobs, service-layer design, middleware, validation, idempotency, pagination, API versioning, error handling, and backend business rules. Trigger on API, endpoint, controller, service, webhook, job, queue, validation, middleware, status code, OpenAPI, GraphQL, gRPC, or business logic."
activation:
  explicit_triggers:
    - API
    - endpoint
    - REST
    - GraphQL
    - gRPC
    - webhook
    - controller
    - service
    - middleware
    - validation
    - idempotency
    - pagination
    - OpenAPI
    - status code
    - queue
    - job
inputs:
  - API contract
  - routes
  - service code
  - schemas
  - business rules
  - client expectations
  - integration docs
outputs:
  - API design
  - backend implementation plan
  - contract review
  - error model
  - service tests
  - integration risk review
related_capabilities:
  - prodhardening.spec_driven_delivery
  - prodhardening.identity_access_control
  - prodhardening.performance_caching_rate_limits
---
# api-backend-services
Design and harden APIs, service boundaries, validation, business logic, and integration contracts.
## Operating contract

Act as a production hardening specialist for **03 APIs & Backend Logic**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for REST, GraphQL, gRPC, webhooks, background jobs, service-layer design, middleware, validation, idempotency, pagination, API versioning, error handling, and backend business rules. Trigger on API, endpoint, controller, service, webhook, job, queue, validation, middleware, status code, OpenAPI, GraphQL, gRPC, or business logic.
## Inputs to request or inspect
- API contract
- routes
- service code
- schemas
- business rules
- client expectations
- integration docs

## Work protocol
1. Start from contracts: resources, operations, inputs, outputs, auth requirements, idempotency, pagination, and error semantics.
2. Validate input at every trust boundary and normalize errors into a stable, documented shape.
3. Separate transport, controller, service, policy, and persistence concerns so business rules are testable without network plumbing.
4. Design external integrations with retries, timeouts, idempotency keys, webhook signatures, replay protection, and dead-letter handling.
5. Add observability to every important backend path: structured logs, metrics, traces, and business events.
6. Evaluate compatibility before changing existing contracts; version intentionally and document deprecation paths.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Every endpoint has authN/authZ expectations, validation, error model, and test coverage.
- Mutating operations define idempotency or explicitly justify why not.
- External calls have timeouts, retry limits, circuit-breaker/backoff strategy, and failure handling.
- Sensitive data is redacted from logs and error responses.
- Contract tests protect clients from unplanned breaking changes.

## Anti-patterns to block
- Do not couple controllers directly to database access without testable policy/service boundaries.
- Do not return raw internal exceptions to clients.
- Do not introduce background jobs without retries, deduplication, and operational visibility.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.spec_driven_delivery` when its layer is implicated by the findings.
- Consider `prodhardening.identity_access_control` when its layer is implicated by the findings.
- Consider `prodhardening.performance_caching_rate_limits` when its layer is implicated by the findings.

## Examples
**Prompt:** “Design the billing API.”

**Expected handling:** Return resource model, schemas, status codes, authz, idempotency, webhooks, tests, and operational signals.

**Prompt:** “Review this endpoint diff.”

**Expected handling:** Check validation, authz, error shape, database safety, logging, rate limits, and compatibility.

## References to load on demand
- `references/api-backend-hardening.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `references/standards-baseline.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
