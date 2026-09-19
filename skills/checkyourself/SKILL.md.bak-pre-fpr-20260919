---
name: checkyourself
description: Evidence-backed pre-launch diagnostics, production scores, approval-gated fixes, learning plans, and optional dashboards for AI-built projects.
---

# CheckYourself

Evidence-first review: start read-only, inspect the launch surface, label
observed/inferred/untested claims, write a bounded Production Reality Report,
and ask before edits. Receipts improve reviewability, not safety.

## Workflow

1. **Load context.** In this repo or a copied `checkyourself` folder, start
   with `CONTEXT.md`, `AGENTS.md`, `rules.md`,
   `02_RUN_DIAGNOSTIC/coverage-matrix.md`, and
   `02_RUN_DIAGNOSTIC/scoring-method.md`; otherwise ask for the smallest missing
   evidence. Infer stack, audience, data shape, deploy target, and risk; label
   guesses.
2. **Run safe deterministic checks.** Prefer read-only commands. Stable
   semantic IDs (for example `CY-SECRET-001` and `CY-CONFIG-001`) support
   suppression, diff, and citation.

```bash
python3 tools/checkyourself.py describe --format json
python3 tools/checkyourself.py scan /path/to/project --deep --format json --no-write
python3 tools/checkyourself.py coverage --emit            # fill with evidence, then:
python3 tools/checkyourself.py score --findings scan.json --coverage coverage.json --format json
python3 tools/checkyourself.py backlog --findings scan.json --format json
python3 tools/checkyourself.py next --findings scan.json --format json
python3 tools/checkyourself.py diff --old baseline.json --new current.json --ci   # regression gate
```

   Treat findings as local observations; do not invent another scoring/backlog
   path. If Python is unavailable, sweep manually and label the score
   hand-computed.

### Manual fallback contract

When the CLI is unavailable, use this canonical rule-ID registry and evidence rubric:

| Rule ID | Canonical manual condition |
|---|---|
| `CY-MANUAL-AUTH-001` | Auth, permission, session, or admin behavior lacks verified server-side evidence. |
| `CY-MANUAL-DATA-001` | Data storage, recovery, retention, or tenant isolation lacks verified evidence. |
| `CY-MANUAL-PRIVACY-001` | Privacy, consent, deletion, or third-party data handling lacks verified evidence. |
| `CY-MANUAL-TEST-001` | A dangerous or launch-critical path lacks a focused test receipt. |
| `CY-MANUAL-RELEASE-001` | Deployment, rollback, CI/CD, or supply-chain behavior lacks a verified receipt. |
| `CY-MANUAL-OBS-001` | Observability, alerting, or incident response lacks a verified receipt. |
| `CY-MANUAL-AI-001` | AI/RAG/agent permissions, evaluation, or refusal behavior lacks verified evidence. |
| `CY-MANUAL-OTHER-001` | A material gap does not match another registered manual condition. |

Reuse a detector ID from the [canonical detector-rule registry](../../docs/cli.md#canonical-detector-rule-registry)
when it matches a shipped detector. Never invent or renumber this registry.

Every manual finding needs registry ID, severity/category, exact dated evidence,
plain-English risk, and status. `Pass` needs reviewer assertions plus a
`checkyourself receipt` bound to one surface, source revision, command, claim,
and result; content and binding hashes must verify. Receipts cannot be reused
across surfaces/claims; caller-authored provenance is not proof. `Finding` needs
evidence of gap and harm; `Unknown` needs an evidence request; `Not applicable`
needs a concrete reason and the same verifier-captured delegation receipt
contract. Without an inspectable artifact, label a low-confidence hand-computed
estimate.

### Deterministic score contract

The executable score is `final_score = min(base_score, minimum_cap)`, where
`base_score` is the rounded sum of clamped category awards after evidence and
unresolved-finding penalties. The cap is the minimum of 100, 49 for unresolved
P0, 74 for unresolved P1, 84 for missing critical evidence, and 90 for missing
high-score launch-gate evidence. `NotApplicable` with a concrete reason and
verified delegation receipt retains its category weight. Accepted/deferred
dispositions do not close residual risk; `--claim` records an accepted claim
without an independent challenge. See the [CLI scoring
contract](../../docs/cli.md#scoring) and [executable
implementation](../../tools/checkyourself.py).

3. **Sweep the surface.** Cover product purpose, frontend UX/accessibility,
   backend/API, auth, data/migrations, secrets/config, tests, CI/CD,
   dependencies, deploy/rollback, observability, performance, privacy,
   compliance, and AI/RAG/agent governance when relevant.
4. **Write the report.** Include purpose; stack/confidence; unknowns;
   Production Reality Score (0–100) with caps (P0 49, P1 74, missing critical
   evidence 84, missing launch-gate evidence 90; no findings is Unknown, never
   automatic Pass); complete Pass/Finding/Unknown/Not applicable coverage;
   P0–P3 findings; evidence; complete backlog; safest first batch; questions;
   and learning seeds.
5. **Recommend before acting.** Each backlog item needs finding ID, severity,
   fix, blast radius, reason, files/systems, verification, rollback, learning
   value, and status. Do not edit until the user approves a named fix/batch.
6. **Loop after approval.** Make the smallest reversible change, verify, update
   status, rescore when evidence changes, and keep accepted-risk, deferred, and
   suppressed dispositions visible as residual risk with owner and trigger.
7. **Teach from findings.** Tie lessons to actual gaps/fixes; give next topics,
   why, 7-day/30-day plans, project exercises, and what to ignore. Each top
   priority gets a trusted written source and, when available, a relevant
   YouTube video; record `source_type`, `authority_level`,
   `why_this_source_is_trusted`, and `checked_at`; the written source is canonical.

The report must sweep every relevant surface and explain plain-English risk
before technical detail. Pass requires evidence; Finding evidence and risk;
Unknown a question/evidence request; Not applicable a reason. The first batch
is not the full scope.

## Example prompts

```text
Use $checkyourself to run a read-only production-readiness diagnostic for this app. Do not change code yet.
```

```text
Use $checkyourself to score this MCP server before launch, list every blocking unknown, and propose the safest first fix batch.
```

```text
Use $checkyourself on this website repo. After the report, make a learning plan from the gaps you found. dashboard inline.
```

## Safety rules

- Start read-only. Without explicit approval, do not change code, install
  dependencies, rotate secrets, touch production, or rewrite architecture.
- Do not invent evidence/inflate the score or paste secrets, customer data,
  proprietary code, unredacted `.env` values, or unnecessary long artifacts.
- For regulated, financial, health, legal, life-safety, security-critical, or
  high-volume systems, recommend qualified expert review.

## Dashboard modes

- Default: no dashboard.
- `dashboard inline`: compact Markdown dashboard.
- `dashboard yes`: self-contained HTML/CSS dashboard from the existing report;
  do not rerun the audit; use the canonical template and complete backlog.

## Voice

Be direct, useful, and evidence-first. Light reality-check tone may target
project state, never the person; high-stakes findings stay blunt and calm.
