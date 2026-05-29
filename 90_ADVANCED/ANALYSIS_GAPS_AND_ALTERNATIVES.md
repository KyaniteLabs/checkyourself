# Gaps, Missed Opportunities, Blind Spots, and Alternatives

This file records the editorial and architectural decisions behind the final model-agnostic capability pack.

## Main corrections from the draft

1. **Removed vendor lock-in from the core.** The original SOP and draft were framed around one skill format. The final pack uses neutral terms: capability, agent, runtime, manifest, references, templates, and gates. `SKILL.md` remains as a compatibility filename, not a dependency.
2. **Added the missing orchestrator.** The draft README mentioned an orchestrator but did not include a capability for it. Production hardening needs a router that classifies risk, selects layers, and synthesizes findings.
3. **Shifted from topic-first to task-first.** The draft mirrored the stack diagram. The final set keeps the stack but defines each file around repeatable work: review, design, harden, verify, release, recover.
4. **Added deterministic gates.** Skills alone cannot enforce production quality. The final pack explicitly routes mandatory controls into tests, scans, policy-as-code, deployment checks, approval gates, telemetry, and runbooks.
5. **Added missing cross-cutting domains.** Testing/evals, configuration/secrets, privacy/compliance, agent/RAG governance, supply-chain provenance, and spec-driven delivery are first-class capabilities.
6. **Separated multi-tenancy/RLS from generic database design.** Tenant isolation is high-risk enough to require its own specialized workflow and negative test plan.
7. **Added publishable packaging.** The final version includes a manifest, router instructions, references, templates, validation script, license, notice, and publication checklist.

## Blind spots to watch

- **Skill overconfidence:** A well-written skill can produce a better review but cannot prove correctness. Enforce through CI, tests, policy, and runtime controls.
- **Checklist theater:** Passing many checkboxes can still miss the business-critical failure mode. Start from user journeys, data sensitivity, and SLOs.
- **Tenant leakage outside the database:** Caches, search indexes, exports, logs, analytics, support tooling, and AI corpora can bypass database isolation if not scoped.
- **AI agent execution risk:** Coding agents can run arbitrary commands. Sandboxes, limited credentials, audit trails, and approval boundaries are mandatory for serious use.
- **RAG trust gap:** Citations are necessary but not sufficient. Retrieval permissions, freshness, chunk provenance, faithfulness evals, and user feedback loops matter.
- **Supply-chain undercoverage:** Dependencies, build provenance, artifact signing, CI token scope, and SBOMs are often missing from prototype-to-prod transitions.
- **Restore illusion:** Backups are not evidence until restored. Measure RTO/RPO through drills.
- **Privacy tail risk:** Deletion and retention must cover logs, backups, analytics, vendors, exports, caches, search, and AI indexes, not just primary rows.

## Alternative ways to cover the solution space

| Approach | Best for | Weakness | Recommendation |
|---|---|---|---|
| Capability/skill pack | Reusable reasoning, agent triggering, consistent reviews | Not deterministic enforcement | Use as the human/agent interface layer. |
| Router/subagent team | Complex multi-step work across specialties | Coordination overhead and context fragmentation | Use for large audits, incidents, migrations, and launch readiness. |
| Policy-as-code | Mandatory security/IaC/org controls | Cannot reason about product intent or trade-offs | Use for non-negotiable gates. |
| Internal developer platform / golden paths | Standardizing teams at scale | Can become rigid or stale | Use for paved roads: service templates, pipelines, observability, deployment. |
| CI/CD quality gates | Repeatable release enforcement | Only sees what is encoded | Use for tests, scans, SBOM/provenance, deploy checks. |
| RAG/knowledge base | Large changing internal docs | Retrieval can be stale or mis-scoped | Use as reference source, not authority for unsafe actions. |
| Event-driven agent arbiter | Enterprise-scale asynchronous work | Operational complexity and governance burden | Use after simpler routing no longer scales. |

## Recommended operating model

Use a **hybrid** model:

1. Capabilities define how agents reason and report.
2. Templates standardize outputs.
3. Deterministic gates enforce mandatory controls.
4. Subagents or routers coordinate complex work.
5. Policy-as-code and CI/CD block unsafe changes.
6. Observability and incident workflows close the loop after release.
