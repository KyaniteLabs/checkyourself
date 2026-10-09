# Scoring Method

Production Reality Score: 0–100 evidence-based readiness estimate, not a
guarantee or production-safety proof.

## Category weights

| Category | Weight |
|---|---:|
| Data, privacy, and tenant/user isolation | 18 |
| Auth, permissions, and session safety | 14 |
| Secrets, environment, and runtime config | 10 |
| API, validation, uploads, and business logic | 10 |
| Testing and quality gates | 10 |
| Deployment, release, rollback, and CI/CD | 8 |
| Observability, logs, errors, and incident response | 8 |
| Performance, scaling, caching, and rate limits | 8 |
| Frontend UX, accessibility, and client safety | 8 |
| AI/RAG/agent governance, if applicable | 6 |

If a category does not apply, mark `NotApplicable`, give
`not_applicable_reason`, and attach a verifier-captured `delegation_receipts`
artifact showing responsibility. A reason alone is Unknown. Do not redistribute
weight: the CLI awards it fully only when the receipt is non-empty, in-root,
hash-matched, and records provenance. Hand scores treat verified NotApplicable
as full credit, matching `score --findings --coverage`.

Prose: **Not applicable**. Coverage JSON: `NotApplicable`.

## Caps

Unresolved P0 caps the final score at 49; unresolved P1 at 74; missing critical
evidence at 84, including estimates. A score above 90 requires credible
evidence for tests, secrets, deployment/rollback, observability, auth, and data
boundaries; this cap also applies to estimates.

## Executable scoring contract

The CLI computes base score and caps deterministically:

1. Start each category at its weight.
2. Subtract the evidence penalty for an `Unknown` category (`100%` for critical
   C1/C2/C3, otherwise `50%`) and unresolved finding penalties: `P0 = 100%`,
   `P1 = 60%`, `P2 = 25%`, `P3 = 10%` of category weight. Clamp to `[0, weight]`.
3. `base_score = round(sum(category_award))`.
4. `minimum_cap = min(100, 49 if unresolved P0, 74 if unresolved P1, 84 if
   critical evidence is missing, 90 if a high-score launch-gate category lacks
   evidence)`.
5. `final_score = min(base_score, minimum_cap)`.

`NotApplicable` with a concrete reason and verified delegation receipt retains
full weight. `accepted-risk`, `deferred`, and `suppressed` are workflow
dispositions, not residual-risk closure; penalties and caps remain until fixed
or proven not applicable. The executable reference is
[`docs/cli.md#scoring`](../docs/cli.md#scoring), backed by
[`tools/checkyourself.py`](../tools/checkyourself.py).

## Confidence labels

**High confidence** — direct repo/config/test evidence. **Medium confidence** —
enough evidence, some assumptions. **Low confidence** — limited context; score
may change significantly.

## Required explanation

For each category: evidence found, missing evidence, awarded points, and score
improvement needed.
