---
id: prodhardening.data_storage_migrations
name: data-storage-migrations
version: 1.0.0
status: stable
layer: "04 Database & Storage"
summary: "Design schemas, migrations, queries, indexes, transactions, storage selection, and data lifecycle controls."
description: "Use this capability for database schema design, SQL/NoSQL selection, migrations, indexing, query review, connection pooling, backups, object storage, event storage, data retention, and data lifecycle planning. Trigger on database, schema, migration, index, SQL, PostgreSQL, MySQL, MongoDB, Redis, S3, ORM, transaction, backup, retention, or data model."
activation:
  explicit_triggers:
    - database
    - schema
    - migration
    - index
    - SQL
    - PostgreSQL
    - MySQL
    - MongoDB
    - Redis
    - ORM
    - transaction
    - backup
    - retention
    - data model
    - object storage
inputs:
  - entity model
  - queries
  - migration files
  - ORM schema
  - access patterns
  - volume estimates
  - retention requirements
outputs:
  - data model
  - migration plan
  - index plan
  - query review
  - backup/restore strategy
  - data lifecycle controls
related_capabilities:
  - prodhardening.multitenancy_rls_isolation
  - prodhardening.privacy_compliance_data_governance
  - prodhardening.availability_recovery_continuity
---
# Capability: data-storage-migrations
Design schemas, migrations, queries, indexes, transactions, storage selection, and data lifecycle controls.
## Operating contract

Act as a production hardening specialist for **04 Database & Storage**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for database schema design, SQL/NoSQL selection, migrations, indexing, query review, connection pooling, backups, object storage, event storage, data retention, and data lifecycle planning. Trigger on database, schema, migration, index, SQL, PostgreSQL, MySQL, MongoDB, Redis, S3, ORM, transaction, backup, retention, or data model.
## Inputs to request or inspect
- entity model
- queries
- migration files
- ORM schema
- access patterns
- volume estimates
- retention requirements

## Work protocol
1. Choose storage from access patterns, consistency needs, query complexity, latency, operational maturity, and failure mode, not fashion.
2. Model entities, relationships, ownership, lifecycle, retention, and deletion semantics before writing migrations.
3. Design migrations for zero or low downtime: expand, backfill, dual-read/write if needed, contract, and cleanup.
4. Review queries with expected cardinality, indexes, lock behavior, transaction isolation, and connection pool impact.
5. Plan backups and restores as executable drills, not documents. Include data corruption and accidental deletion scenarios.
6. Treat caches and search indexes as derived data unless explicitly designed as source of truth.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Every schema change has forward migration, rollback/roll-forward plan, and data backfill strategy.
- Every high-volume query has an index or explicit performance rationale.
- Every data store has backup, restore, retention, and deletion behavior defined.
- Every transaction boundary is intentional and avoids long locks in user-facing paths.
- Production migrations are rehearsed with realistic data volume or a safe proxy.

## Anti-patterns to block
- Do not deploy destructive migrations in the same release that still depends on old fields.
- Do not assume ORM-generated queries are efficient without checking plans.
- Do not create caches that bypass authorization or tenant boundaries.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.multitenancy_rls_isolation` when its layer is implicated by the findings.
- Consider `prodhardening.privacy_compliance_data_governance` when its layer is implicated by the findings.
- Consider `prodhardening.availability_recovery_continuity` when its layer is implicated by the findings.

## Examples
**Prompt:** “Add organizations and teams to the data model.”

**Expected handling:** Produce entities, relationships, constraints, indexes, migrations, access patterns, and test data.

**Prompt:** “Why is this query slow?”

**Expected handling:** Inspect plan, cardinality, indexes, locks, data shape, and application call patterns.

## References to load on demand
- `references/data-storage-hardening.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `references/production-readiness-gates.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
