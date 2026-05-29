# API & Backend Hardening Reference

## Endpoint checklist

- Resource and action are clear
- AuthN and AuthZ are explicit
- Input schema and output schema exist
- Error format is stable
- Idempotency is defined for mutation/retry paths
- Pagination and filtering have limits
- Rate limit or abuse model exists for public/expensive endpoints
- Logs/metrics/traces include correlation and redaction
- Contract tests protect clients

## Error response shape

Prefer a stable problem-details-style shape:

```json
{
  "type": "https://example.com/errors/validation",
  "title": "Validation failed",
  "status": 400,
  "detail": "One or more fields are invalid.",
  "request_id": "req_...",
  "errors": [{"field":"email","message":"Invalid email"}]
}
```

## Integration resilience

- Timeouts on every external call
- Retries only for safe or idempotent operations
- Exponential backoff with jitter
- Circuit breakers for repeated dependency failures
- Dead-letter queues for asynchronous processing
- Webhook signatures and replay protection
