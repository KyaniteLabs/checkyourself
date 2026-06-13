---
id: prodhardening.privacy_compliance_data_governance
name: privacy-compliance-data-governance
version: 1.0.0
status: stable
layer: "18 Privacy, Compliance & Data Governance"
summary: "Operationalize privacy, compliance, data classification, retention, consent, deletion, auditability, and evidence management."
description: "Use this capability for PII, PHI, PCI, GDPR/CCPA-style obligations, consent, retention, deletion, DSAR/export, data classification, data residency, audit evidence, compliance controls, records of processing, and privacy-by-design reviews."
activation:
  explicit_triggers:
    - privacy
    - compliance
    - PII
    - PHI
    - PCI
    - GDPR
    - CCPA
    - consent
    - retention
    - deletion
    - DSAR
    - data export
    - data classification
    - data residency
    - audit evidence
    - privacy review
inputs:
  - data inventory
  - user flows
  - legal/compliance obligations
  - region requirements
  - retention rules
  - vendors/processors
  - audit requirements
outputs:
  - data classification
  - privacy risk review
  - retention/deletion plan
  - consent/audit model
  - compliance evidence checklist
related_capabilities:
  - prodhardening.data_storage_migrations
  - prodhardening.security_privacy_threat_modeling
  - prodhardening.ai_agent_rag_governance
---
# privacy-compliance-data-governance
Operationalize privacy, compliance, data classification, retention, consent, deletion, auditability, and evidence management.
## Operating contract

Act as a production hardening specialist for **18 Privacy, Compliance & Data Governance**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for PII, PHI, PCI, GDPR/CCPA-style obligations, consent, retention, deletion, DSAR/export, data classification, data residency, audit evidence, compliance controls, records of processing, and privacy-by-design reviews.
## Inputs to request or inspect
- data inventory
- user flows
- legal/compliance obligations
- region requirements
- retention rules
- vendors/processors
- audit requirements

## Work protocol
1. Classify data by sensitivity, subject, tenant, source, purpose, retention, residency, and downstream sharing.
2. Collect only data needed for defined purposes and document why it is needed.
3. Design consent, preference, audit, and deletion flows as product features, not backend afterthoughts.
4. Map vendors, subprocessors, analytics, logs, backups, exports, AI retrieval corpora, and support tools into the data flow.
5. Define retention, legal hold, deletion, anonymization, and backup reconciliation behavior.
6. Produce evidence artifacts that auditors, customers, and future maintainers can verify.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Every sensitive data element has purpose, retention, access, encryption, logging, and deletion behavior defined.
- Privacy-sensitive events are auditable without exposing unnecessary sensitive content.
- Exports and DSAR-like flows respect tenant, identity, and authorization boundaries.
- AI/RAG corpora do not ingest private data without access control, retention, and deletion strategy.
- Compliance exceptions have owner, approval, scope, and expiration.

## Anti-patterns to block
- Do not assume deleting primary rows deletes data from logs, caches, backups, analytics, and AI indexes.
- Do not collect “maybe useful later” personal data without a purpose and retention plan.
- Do not treat compliance as paperwork detached from implementation.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.data_storage_migrations` when its layer is implicated by the findings.
- Consider `prodhardening.security_privacy_threat_modeling` when its layer is implicated by the findings.
- Consider `prodhardening.ai_agent_rag_governance` when its layer is implicated by the findings.

## Examples
**Prompt:** “We need to support account deletion.”

**Expected handling:** Trace all data stores, logs, backups, vendors, caches, search indexes, and AI corpora; define deletion evidence.

**Prompt:** “Review this analytics setup for privacy.”

**Expected handling:** Classify events, PII, consent, retention, vendor sharing, user rights, and audit evidence.

## References to load on demand
- `../../references/privacy-data-governance.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `../../templates/privacy-review.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
