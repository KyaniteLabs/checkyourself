# Privacy, Compliance & Data Governance Reference

## Data inventory fields

- Data element
- Sensitivity class
- Data subject
- Tenant/customer scope
- Source
- Purpose
- Storage location
- Retention period
- Deletion/anonymization behavior
- Sharing/vendors
- Access controls
- Audit evidence

## Lawful basis and consent (GDPR/CCPA)

- **Lawful basis (GDPR Art. 6):** every processing purpose needs one — consent, contract, legal obligation, vital interest, public task, or legitimate interest. Auditors check that each purpose in the data inventory maps to a documented basis, and that "legitimate interest" cases have a balancing test on file.
- **Consent must be opt-in, granular, and revocable.** Pre-ticked boxes, "by using this site you agree", and bundled consent are non-compliant. Look for: a real reject path, separate toggles per purpose (analytics vs marketing vs functional), and a stored consent record (who/when/what version of the policy).
- **Cookie banner / non-essential trackers:** no analytics, ad, or marketing scripts may load before consent. Detectable failure: GA/Meta Pixel/`gtag`/third-party tags firing on page load regardless of the banner; consent stored but never enforced against the tag loader.
- **CCPA/CPRA:** a clear "Do Not Sell or Share My Personal Information" link, honoring of Global Privacy Control (GPC) signals, and no discrimination against users who opt out.

## DSAR and right to erasure mechanics

A data-subject access/erasure request (GDPR Art. 15/17, CCPA deletion right) must be honored within the statutory window (GDPR: **without undue delay, within 1 month**; extendable to 3 for complex cases). Deletion is not a single `DELETE` — it must cascade across every place the data landed.

Erasure/deletion must reach, and the audit should confirm coverage of:

| Location | What to do | Common miss |
|---|---|---|
| Primary store (DB) | Hard-delete or anonymize; cascade FKs | Soft-delete flag only, row still present |
| Read replicas / standbys | Propagates via replication | Lagging or detached replica retains data |
| Caches (Redis, CDN, app cache) | Invalidate keys | Cached profile/PII survives for TTL |
| Search indexes (Elastic, Algolia, pgvector) | Delete documents | Index keeps a searchable copy |
| Analytics / event stores | Delete or pseudonymize events | Mixpanel/Amplitude/warehouse keeps PII |
| Logs and traces | Purge or never log PII | PII in app/LLM trace logs is permanent leak |
| Backups | Document age-out; suppress on restore | Restoring a backup resurrects deleted user |
| LLM corpora / vector stores | Remove embeddings + source | RAG keeps user content indexed |
| Third-party processors | Propagate deletion via API/DPA | Vendor (Stripe, email, support) still holds it |
| Exports / data dumps / S3 | Track and delete | Orphaned CSV/export with PII |

Backups are the standard exception: it is acceptable to age them out on the normal retention cycle rather than surgically edit them, **if** that policy is documented and a restored record carries a deletion suppression/re-deletion step. An auditor verifies the deletion routine enumerates these sinks, not just the primary table.

## Retention schedules and automated deletion

- Every data class needs a **defined retention period** and an automated mechanism to delete/anonymize at expiry (TTL, scheduled job, lifecycle policy on object storage, log retention config). "Keep forever by default" is a finding.
- Check for: object-storage lifecycle rules, log/trace retention TTLs, DB cron purges, and short TTLs on PII-bearing caches.
- Anonymization must be irreversible (no re-identification via join keys) to count as "no longer personal data".

## Data residency

- Know where data physically lives (region) and whether that satisfies contractual/legal residency (EU data stays in EU, etc.).
- Cross-border transfer (e.g. EU → US) needs a transfer mechanism (SCCs, adequacy). Check serverless/edge region config and provider region pinning.
- Confirm sub-processors (LLM provider, analytics, email) are covered and located acceptably.

## Breach notification

- **GDPR:** notify the supervisory authority within **72 hours** of becoming aware of a personal-data breach; notify affected individuals without undue delay if high risk.
- **CCPA/state laws:** notify affected residents in the most expedient time possible.
- Auditors check for an incident/breach runbook with the 72h clock, a contact path to the DPO/authority, and a log of what data and which subjects were affected.

## Records of processing and processors

- **Records of Processing Activities (RoPA, GDPR Art. 30):** maintained list of processing purposes, categories of data/subjects, recipients, transfers, and retention.
- **Data Processing Agreements (DPA)** with every processor/sub-processor (cloud, LLM provider, analytics, email, support, payments).
- **DPIA** for high-risk processing (large-scale profiling, sensitive data, AI decisioning).

## PII in logs, traces, and LLM prompts

The single most common leak in AI-built apps. "PII in logs/traces/LLM prompts" means personal data is written, in clear, to a place it was never inventoried for and may never be deleted:

- Application logs / `console.log` of request bodies, user objects, or errors containing PII.
- Tracing/observability backends (OpenTelemetry, Sentry, Datadog) capturing full payloads.
- LLM prompt/completion traces (LangSmith, Langfuse, Helicone) storing whatever the user pasted plus retrieved context — often sent to a third party with its own retention.
- These copies are usually **not** covered by the deletion cascade above, so they silently violate retention and erasure obligations.

Remediation: scrub PII before logging, disable full-payload capture for PII-bearing routes, set retention TTLs on all log/trace stores, and add these stores to the erasure cascade. See `ai-agent-rag-governance.md` for the LLM-specific redaction detail.

## Deletion review

Deleting an account or record may require action across primary stores, replicas, caches, search indexes, analytics, logs, exports, backups, AI corpora, vendors, and support tooling. Define what is deleted immediately, what ages out, what is anonymized, and what is retained under legal or operational obligation.
