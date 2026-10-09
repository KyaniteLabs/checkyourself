---
id: prodhardening.performance_caching_rate_limits
name: performance-caching-rate-limits
version: 1.0.0
status: stable
layer: "13 Performance, Caching & Rate Limits"
summary: "Improve latency and throughput with measurement, caching, CDN strategy, rate limits, backpressure, and abuse controls."
description: "Use this capability for performance optimization, load tests, k6/JMeter/Locust plans, caching, Redis, CDN, Cache-Control, invalidation, rate limiting, quotas, token bucket, sliding window, 429 behavior, abuse protection, and cost-based throttling."
activation:
  explicit_triggers:
    - performance
    - latency
    - throughput
    - load test
    - k6
    - JMeter
    - Locust
    - cache
    - Redis
    - CDN
    - Cache-Control
    - invalidation
    - rate limit
    - quota
    - token bucket
    - 429
    - abuse
    - throttle
inputs:
  - SLOs
  - traffic estimates
  - logs/metrics/traces
  - endpoint list
  - cache candidates
  - rate-limit policy
  - load-test scripts
outputs:
  - performance plan
  - cache design
  - rate-limit design
  - load-test plan
  - bottleneck analysis
  - abuse/cost control review
related_capabilities:
  - prodhardening.scaling_load_resilience
  - prodhardening.observability_sre_incident_response
  - prodhardening.api_backend_services
---
# Capability: performance-caching-rate-limits
Improve latency and throughput with measurement, caching, CDN strategy, rate limits, backpressure, and abuse controls.
## Operating contract

Act as a production hardening specialist for **13 Performance, Caching & Rate Limits**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for performance optimization, load tests, k6/JMeter/Locust plans, caching, Redis, CDN, Cache-Control, invalidation, rate limiting, quotas, token bucket, sliding window, 429 behavior, abuse protection, and cost-based throttling.
## Inputs to request or inspect
- SLOs
- traffic estimates
- logs/metrics/traces
- endpoint list
- cache candidates
- rate-limit policy
- load-test scripts

## Work protocol
1. Start with a measurable hypothesis: metric, baseline, target, traffic model, dataset, and expected bottleneck.
2. Optimize in order: eliminate unnecessary work, fix data access, add caching, tune concurrency, then scale infrastructure.
3. Design cache keys with tenant/user/permission dimensions. Define freshness, invalidation, stampede protection, and fallback behavior.
4. Design rate limits by actor, endpoint cost, tenant tier, authentication state, and abuse case. Return useful 429 responses with retry guidance.
5. Load-test the system and the load generator. Watch generator CPU, memory, network, and file descriptor limits to avoid false results.
6. Connect performance work to observability: latency percentiles, saturation, error rate, queue depth, cache hit ratio, and cost.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Performance claims include reproducible measurement and representative data/traffic assumptions.
- Cache keys cannot leak or mix tenant/user/permission-scoped data.
- Rate limits protect login, expensive endpoints, public APIs, webhooks, and AI/model calls where relevant.
- Load tests define success thresholds and failure interpretation before running.
- Optimization does not remove correctness, security, or observability controls.

## Anti-patterns to block
- Do not add global cache keys for scoped data.
- Do not benchmark with a saturated load generator and trust the latency numbers.
- Do not rate-limit only by IP when authenticated actor or tenant is the real cost/security boundary.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.scaling_load_resilience` when its layer is implicated by the findings.
- Consider `prodhardening.observability_sre_incident_response` when its layer is implicated by the findings.
- Consider `prodhardening.api_backend_services` when its layer is implicated by the findings.

## Examples
**Prompt:** “This API is slow.”

**Expected handling:** Check baseline, query plans, trace spans, cache candidates, concurrency, and SLO impact.

**Prompt:** “Add rate limits to our AI endpoint.”

**Expected handling:** Design actor tiers, token/cost accounting, burst limits, 429 UX, abuse cases, and monitoring.

## References to load on demand
- `../../references/performance-caching-rate-limits.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `../../templates/performance-test-plan.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
