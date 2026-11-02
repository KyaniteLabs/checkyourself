# Performance, Caching & Rate Limits Reference

## Cache design checklist

- What is cached?
- Who is allowed to see it?
- What is the key?
- What is the TTL?
- How is it invalidated?
- What happens on cache miss?
- What happens on stale cache?
- How are stampedes prevented?
- How are hit ratio and evictions measured?

## Rate-limit design checklist

- Actor key: IP, user, tenant, API key, or composite
- Algorithm: fixed window, sliding window, token bucket, leaky bucket
- Burst and sustained rates
- Cost weighting for expensive operations
- 429 response and retry headers
- Bypass and admin policy
- Observability and alerting

## Load generator sanity checks

Watch CPU, memory, network throughput, open file descriptors, and request-generation errors. A saturated generator invalidates target latency conclusions.
