# Scoring Method

The Production Reality Score is a 0–100 readiness confidence score.

It is not a moral judgment and not a guarantee. It is an evidence-based estimate of how ready the app is for real users.

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

If a category does not apply, redistribute its points across the most relevant categories and state why.

## Caps

- Any unresolved P0 caps the final score at 49.
- Any unresolved P1 caps the final score at 74.
- Missing evidence in a critical category caps the final score at 84.
- A score above 90 requires credible evidence for tests, secrets handling, deployment/rollback, observability, auth, and data boundaries.

## Confidence labels

Every score must include a confidence label:

- **High confidence** — direct repo/config/test evidence.
- **Medium confidence** — enough evidence, but some assumptions.
- **Low confidence** — limited context; score may change significantly.

## Required explanation

For each category, say:

- what evidence was found;
- what was missing;
- what points were awarded;
- what would raise the score.
