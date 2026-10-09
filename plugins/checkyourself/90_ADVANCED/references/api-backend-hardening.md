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

## Webhook signature verification and idempotency

Two distinct failure modes cause double-charges and replay fraud. They are separate controls — having one does not give you the other.

**1. Signature verification (authenticity).** A webhook endpoint is a public URL; anyone can POST to it. Without signature verification, an attacker forges "payment succeeded" events. Verify the cryptographic signature on **every** webhook before trusting the body.

- **Stripe:** verify the `Stripe-Signature` header with `stripe.webhooks.constructEvent(rawBody, sig, endpointSecret)`. This must run on the **raw request body** — parsing JSON first (or any middleware that re-serializes) breaks the HMAC and is a common silent failure. The `whsec_...` signing secret is per-endpoint; never skip verification in prod.
- General: HMAC-SHA256 over the raw payload, constant-time comparison, reject on mismatch with 400.
- **Replay window:** the signature scheme includes a timestamp (Stripe's `t=`); reject events older than a tolerance (e.g. 5 minutes) so a captured-and-resent request can't be replayed later.

What an auditor looks for: webhook handlers that read/trust the JSON body with no signature check; verification run against parsed (not raw) body; signing secret missing/hardcoded; no timestamp/replay tolerance; verification disabled in dev branches that ship.

**2. Idempotency (exactly-once effect).** Networks retry. Stripe and most providers deliver webhooks **at least once** — the same event arrives multiple times. Clients also retry POSTs. Without idempotency, a retried "charge" or "create order" runs twice.

- **Inbound webhooks:** store the event id (e.g. `evt_...`) and skip if already processed. Make processing idempotent at the DB level (unique constraint on event id, upsert) — not just an in-memory `Set`, which is per-instance and lost on cold start.
- **Outbound/mutating API calls:** accept an `Idempotency-Key` header on POST/charge/order-create routes; persist the key + result, and return the stored result on replay instead of re-executing. Pass idempotency keys through to providers (Stripe supports `idempotencyKey`).
- Use DB unique constraints / transactions to make "create once" atomic under concurrency.

What an auditor looks for: webhook handlers with no dedupe on event id; payment/order creation with no idempotency key; in-memory-only dedupe; non-atomic check-then-create races.

## Input validation and output encoding

- **Validate every input** against a schema at the boundary (Zod, Pydantic, JSON Schema) — body, query, params, headers. Reject unknown fields; bound array lengths, string sizes, and numeric ranges. Do not trust client-supplied IDs, prices, roles, or flags.
- **Parameterize** all queries (bound params/ORM) — never string-build SQL/NoSQL from input. Same for shell (arg arrays, no `shell: true`), file paths (no traversal), and outbound URLs (allow-list, no SSRF).
- **Output encoding:** encode/escape data for its sink — HTML-escape on render, set `Content-Type` correctly, return JSON as JSON. Avoid reflecting raw input into HTML.
- **Mass-assignment:** allow-list which fields a request may set; never spread the whole request body into a DB update.

## Rate limiting and abuse

- Rate limit public, auth, and expensive endpoints (login, signup, password reset, search, anything calling an LLM or third party). Key by user/tenant/IP/API key.
- Use a **shared store** (Redis/Upstash/Durable Object/platform rate limiter) — in-memory limiters are per-instance and don't hold under serverless/horizontal scale.
- Add quotas/spend caps for cost-bearing endpoints; return `429` with `Retry-After`.
- Protect against enumeration and brute force (lockout/backoff on auth), and bot abuse on unauthenticated forms.

## AuthN/AuthZ on every route — including admin

- **Authentication on every non-public route.** Verify the session/JWT server-side; never trust a client-sent role/id. Check token expiry and signature.
- **Authorization (object-level) on every route.** The most common API flaw (BOLA/IDOR): the user is authenticated but the handler fetches `resource[id]` without checking the resource belongs to them. Every read/write must confirm the caller owns or may access *that specific* object/tenant.
- **Admin and internal routes are routes too.** `/admin`, internal APIs, cron/job endpoints, debug routes, and GraphQL fields must enforce authz — not rely on "no link to it" or being on a "private" path. Look for admin endpoints guarded only by obscurity, cron routes with no shared-secret/header check, and `/debug`/`/dev` endpoints shipped to prod.
- Enforce authz at the data layer where possible (e.g. row-level security) so a missing app-layer check doesn't expose data.

## File-upload safety

- Validate type by content (magic bytes), not just extension or client `Content-Type`; enforce a size limit.
- Store outside the web root / in object storage; never serve uploads from a path that can execute (no `.php`/`.js` execution).
- Generate server-side filenames; reject path traversal (`../`) in supplied names.
- Use signed/expiring URLs for direct-to-storage upload/download (also avoids serverless payload limits).
- Scan for malware where relevant; set `Content-Disposition: attachment` and a strict `Content-Type` on download; serve user content from a separate origin/domain to contain XSS.

## Integration resilience

- Timeouts on every external call
- Retries only for safe or idempotent operations
- Exponential backoff with jitter
- Circuit breakers for repeated dependency failures
- Dead-letter queues for asynchronous processing
- Webhook signatures and replay protection
