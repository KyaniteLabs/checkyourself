---
id: prodhardening.scaling_load_resilience
name: scaling-load-resilience
version: 1.0.0
status: stable
layer: "14 Load Balancing & Scaling"
summary: "Design scalable, fault-tolerant runtime architectures with load balancing, autoscaling, queues, circuit breakers, and chaos validation."
description: "Use this capability for load balancing, autoscaling, horizontal scaling, capacity planning, queues, workers, circuit breakers, retries, timeouts, backpressure, bulkheads, thundering herd control, graceful degradation, chaos testing, and resilience patterns."
activation:
  explicit_triggers:
    - load balancer
    - autoscale
    - horizontal scaling
    - capacity
    - queue
    - worker
    - circuit breaker
    - retry
    - timeout
    - backpressure
    - bulkhead
    - thundering herd
    - degrade
    - chaos
    - resilience
inputs:
  - traffic model
  - runtime topology
  - SLOs
  - autoscaling rules
  - queue config
  - dependency map
  - failure history
outputs:
  - scaling architecture
  - capacity model
  - resilience design
  - chaos test plan
  - degradation/runbook strategy
related_capabilities:
  - prodhardening.performance_caching_rate_limits
  - prodhardening.availability_recovery_continuity
  - prodhardening.cloud_infrastructure_iac
---
# Capability: scaling-load-resilience
Design scalable, fault-tolerant runtime architectures with load balancing, autoscaling, queues, circuit breakers, and chaos validation.
## Operating contract

Act as a production hardening specialist for **14 Load Balancing & Scaling**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for load balancing, autoscaling, horizontal scaling, capacity planning, queues, workers, circuit breakers, retries, timeouts, backpressure, bulkheads, thundering herd control, graceful degradation, chaos testing, and resilience patterns.
## Inputs to request or inspect
- traffic model
- runtime topology
- SLOs
- autoscaling rules
- queue config
- dependency map
- failure history

## Work protocol
1. Classify components as stateless, stateful, queue-based, singleton, external dependency, or user-facing critical path.
2. Design scaling around bottlenecks: CPU, memory, network, database connections, locks, queue depth, third-party limits, and cost.
3. Apply resilience patterns at boundaries: timeouts, retries with backoff/jitter, circuit breakers, bulkheads, idempotency, and backpressure.
4. Plan load balancer behavior: health checks, drain, sticky sessions only when required, TLS termination, and regional routing.
5. Model graceful degradation: what to disable, defer, cache, serve stale, or queue when dependencies fail.
6. Validate with load and chaos experiments that target real failure modes and define abort conditions.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Autoscaling signals are tied to user impact and saturation, not only average CPU.
- Retries are bounded, jittered, and never amplify outages across services.
- Workers and web requests are idempotent or protected from duplicate processing.
- Critical dependencies have fallback, timeout, or clear user-facing failure behavior.
- Chaos experiments are bounded, reversible, observable, and scheduled with owner approval.

## Anti-patterns to block
- Do not scale app servers while the database connection pool is the bottleneck.
- Do not add retries without timeouts and backoff.
- Do not use sticky sessions to hide unsafe stateful application design unless there is no better option.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.performance_caching_rate_limits` when its layer is implicated by the findings.
- Consider `prodhardening.availability_recovery_continuity` when its layer is implicated by the findings.
- Consider `prodhardening.cloud_infrastructure_iac` when its layer is implicated by the findings.

## Examples
**Prompt:** “Can this handle 10x traffic?”

**Expected handling:** Return capacity model, bottleneck analysis, scaling plan, load-test design, and degradation strategy.

**Prompt:** “Add a queue for emails.”

**Expected handling:** Design idempotency, retries, DLQ, rate limits, observability, and operational runbook.

## References to load on demand
- `../../references/scaling-resilience.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `../../templates/performance-test-plan.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
