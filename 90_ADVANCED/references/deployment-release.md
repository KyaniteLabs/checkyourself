# Deployment & Release Reference

## Safe deployment checklist

- Artifact built once and promoted
- Environment variables validated
- Database compatibility confirmed
- Health checks and smoke tests ready
- Observability dashboards open
- Rollback/roll-forward documented
- Support and incident channel identified
- Feature flags and kill switches verified

## Deployment strategies

- Rolling: simple, requires backward compatibility.
- Blue-green: fast rollback, higher duplicate environment cost.
- Canary: low blast radius, requires traffic routing and telemetry.
- Feature flag rollout: controls behavior independently from artifact deploy.

## Edge and serverless gotchas

Modern AI-built apps default to serverless/edge (Vercel functions, Cloudflare Workers, Netlify functions, Fly Machines, Lambda). The runtime constraints below cause production failures that work fine locally:

- **Cold starts.** First request after idle pays init latency; heavy top-level imports, large bundles, and DB-connection setup at module load make it worse. Check for connection pooling that fights serverless (each instance opening its own pool exhausts DB connections — use a pooler like PgBouncer/Prisma Accelerate/Neon/Hyperdrive, or serverless-driver HTTP).
- **Function timeout limits.** Vercel functions cap execution (seconds; longer needs Fluid/streaming or background jobs); Cloudflare Workers bill CPU time and limit wall time; Lambda caps at 15 min. Long LLM/agent loops and big report generations exceed these — they need streaming, queues, or a durable/background execution path. The agent loop's own timeout must sit *inside* the platform timeout.
- **Payload / response size limits.** Request and response bodies are capped (e.g. a few MB on many platforms). Large file uploads/downloads must go direct to object storage via signed URLs, not through the function.
- **Node APIs unavailable in Edge runtimes.** The Edge runtime (Vercel Edge, Cloudflare Workers) is not Node: no `fs`, no `net`/raw TCP, limited `crypto`, no native addons, many `node:` built-ins absent. Libraries that assume Node (some DB drivers, `bcrypt`, filesystem use) break at runtime, not build time. Verify the route's declared runtime (`export const runtime = 'edge'` vs `'nodejs'`) matches what its dependencies actually need.
- **Statelessness / no local disk.** No durable local filesystem; `/tmp` is ephemeral and per-instance. In-memory state, local caches, uploaded temp files, and "write a file then read it" patterns do not survive between requests or across instances. Use object storage, KV, or a DB. In-memory rate limiters and counters are per-instance and effectively useless at scale.

## Platform config checks

Verify the platform config file exists and matches the app's needs:

- **`vercel.json`** — runtime/region pinning, function `maxDuration` and `memory`, route rewrites/headers, cron jobs. Check that secrets are referenced (not inlined) and `maxDuration` is high enough for long routes.
- **`wrangler.toml` (Cloudflare Workers)** — `compatibility_date`/`compatibility_flags` (drift causes behavior changes), bindings (KV, R2, D1, Durable Objects, secrets via `wrangler secret`, not committed), `routes`, and `node_compat`/`nodejs_compat` flag if Node APIs are used.
- **`fly.toml` (Fly.io)** — `[http_service]` health checks, `internal_port`, `[[vm]]` size, `min_machines_running`, regions, and `release_command` for migrations. Confirm a health check is defined so deploys gate on it.
- **`netlify.toml`** — build command, publish dir, function/edge-function config, redirects, headers, context-specific env (`[context.production]` vs `[context.deploy-preview]`).
- **`render.yaml`** — service type, `healthCheckPath`, `autoDeploy`, env groups, and `preDeployCommand` for migrations.

## Environment promotion and secret management

- **Promote one artifact** across environments (dev → preview/staging → prod); do not rebuild per environment.
- **Separate secrets per environment.** Production secrets must never appear in preview/dev. Check the platform's env scoping (Vercel env per-environment, Cloudflare per-Worker secrets, Fly secrets, Netlify context env). Secrets belong in the platform secret store, never in `vercel.json`/`wrangler.toml`/repo/`.env` committed to git.
- **Validate env at boot** (schema-check required vars; fail fast with a clear message rather than a runtime 500 deep in a request).
- Rotate keys on exposure; confirm preview deploys don't get prod database/LLM keys.

## Health checks, readiness, and rollback per platform

- **Health/readiness endpoint** that checks real dependencies (DB reachable, migrations applied, critical downstreams) — not a static `200 OK`. Deploys should gate on it.
- **Rollback mechanics:** Vercel — instant rollback to a previous immutable deployment (promote a prior build); Cloudflare — `wrangler rollback` / Versions; Fly — redeploy previous image / `fly releases`; Netlify/Render — restore a prior deploy. Confirm the team knows the exact command and that DB migrations are backward-compatible so rolling back code doesn't break the schema (expand/contract migrations).
- **Kill switch / feature flag** to disable a risky feature without redeploying.

## Preview/production parity

- Preview deploys should run the same build, runtime, and migrations as prod, with their own (non-prod) data and secrets.
- Watch for parity gaps that hide bugs until prod: edge vs node runtime differences, different region/latency to the DB, env vars present in prod but missing in preview, and seed/empty data masking real-data edge cases.
- Run smoke tests against the preview URL before promoting.
