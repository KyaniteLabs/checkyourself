# Scaling & Resilience Reference

## Resilience controls

- Timeout every dependency call
- Retry only bounded, idempotent, safe operations
- Add backoff and jitter
- Use circuit breakers for repeated failures
- Bulkhead critical resources
- Apply backpressure before collapse
- Queue work that can be deferred
- Degrade non-critical features deliberately

## Chaos experiment template

1. Hypothesis
2. Blast radius
3. Preconditions
4. Fault injected
5. Expected signals
6. Abort conditions
7. Recovery steps
8. Lessons and follow-up changes
