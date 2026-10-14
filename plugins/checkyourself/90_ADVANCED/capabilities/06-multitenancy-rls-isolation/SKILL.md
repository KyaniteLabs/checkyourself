---
id: prodhardening.multitenancy_rls_isolation
name: multitenancy-rls-isolation
version: 1.0.0
status: stable
layer: "06 Tenant Isolation & RLS"
summary: "Harden multi-tenant systems with database-enforced isolation, tenant-aware caches, and cross-tenant negative tests."
description: "Use this capability whenever multi-tenancy, tenant isolation, Row-Level Security, shared-schema SaaS, organization-scoped data, tenant_id, database policies, cross-tenant access, or tenant-aware caching appears. Trigger even if the user only says \u201corgs\u201d, \u201cworkspaces\u201d, \u201cteams\u201d, \u201ccustomers\u201d, or \u201cB2B SaaS\u201d."
activation:
  explicit_triggers:
    - multi-tenant
    - tenant isolation
    - RLS
    - row-level security
    - shared schema
    - tenant_id
    - workspace
    - organization
    - B2B SaaS
    - cross-tenant
    - policy
inputs:
  - tenant model
  - database schema
  - queries
  - auth claims
  - cache keys
  - service roles
  - migration plan
outputs:
  - tenant isolation design
  - RLS policy plan
  - negative test suite
  - cache isolation review
  - service-account risk map
related_capabilities:
  - prodhardening.data_storage_migrations
  - prodhardening.identity_access_control
  - prodhardening.security_privacy_threat_modeling
---
# multitenancy-rls-isolation
Harden multi-tenant systems with database-enforced isolation, tenant-aware caches, and cross-tenant negative tests.
## Operating contract

Act as a production hardening specialist for **06 Tenant Isolation & RLS**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability whenever multi-tenancy, tenant isolation, Row-Level Security, shared-schema SaaS, organization-scoped data, tenant_id, database policies, cross-tenant access, or tenant-aware caching appears. Trigger even if the user only says “orgs”, “workspaces”, “teams”, “customers”, or “B2B SaaS”.
## Inputs to request or inspect
- tenant model
- database schema
- queries
- auth claims
- cache keys
- service roles
- migration plan

## Work protocol
1. Classify tenant scope for every table, object, file, cache key, search index, queue, and analytics event.
2. Prefer database-enforced tenant isolation for shared-schema relational data. Application filters are not enough for high-risk tenant boundaries.
3. Set tenant context transaction-locally where supported, then run queries through roles that cannot bypass isolation.
4. Use restrictive write checks so inserts and updates cannot assign data to another tenant.
5. Build dual-tenant fixtures and negative tests that prove reads, writes, lists, aggregates, exports, caches, and background jobs cannot cross tenants.
6. Create a documented bypass matrix for admin, support, migration, analytics, and break-glass flows.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Every tenant-scoped table has an isolation policy, tenant_id index where needed, and write constraint.
- Every cache/search/blob/key includes tenant scope or uses a separate isolated namespace.
- Connection pooling cannot leak tenant context between requests.
- All tenant bypasses are explicit, logged, reviewed, and unavailable to ordinary application roles.
- Cross-tenant tests cover API, database, background job, export, cache, and analytics paths.

## Anti-patterns to block
- Do not rely only on “WHERE tenant_id = …” in application code for critical isolation.
- Do not use superuser or bypass roles for normal application traffic.
- Do not create global cache keys for tenant-scoped data.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.data_storage_migrations` when its layer is implicated by the findings.
- Consider `prodhardening.identity_access_control` when its layer is implicated by the findings.
- Consider `prodhardening.security_privacy_threat_modeling` when its layer is implicated by the findings.

## Examples
**Prompt:** “Add workspaces to this SaaS app.”

**Expected handling:** Return tenant ownership model, RLS policy design, cache key strategy, service role matrix, and negative tests.

**Prompt:** “Review these RLS policies.”

**Expected handling:** Check USING/WITH CHECK symmetry, FORCE behavior, indexes, connection-pool safety, bypass roles, and fixtures.

## References to load on demand
- `../../references/multitenancy-rls.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `../../templates/tenant-isolation-test-plan.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
