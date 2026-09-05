# Optional Dashboard Output

Default: no dashboard. Generate only for a requested visual/HTML summary. The
Production Reality Report and complete backlog remain the source of truth.

## Modes

| Request | Output |
|---|---|
| `dashboard` not requested | Markdown report only |
| `dashboard inline` | Compact Markdown fallback |
| `dashboard yes` | One self-contained HTML/CSS dashboard after the report |

For HTML, use the single canonical template in `10_DASHBOARD/`; never create a
second JavaScript/data-template dashboard.

## Show

App/stack; score/confidence; P0/P1/P2/P3 counts and blockers; surface coverage;
complete ID-based findings; waves/next approval; and learning priorities with
source/YouTube links.
Bilingual labels/content require an explicit second-language request or
confirmed inferred candidate. Use evidence-first, lightly opinionated,
non-mean-spirited voice.

## Token and safety rules

- Never generate HTML unless requested or duplicate every report paragraph.
- Keep HTML self-contained and HTML/CSS-only: no external scripts, fonts,
  remote images, or analytics.
- If HTML/CSS is declined, use `10_DASHBOARD/inline-dashboard.md`.
- Use short, predictable, high-contrast sections for ADHD, autism, and
  dyslexia; expose no internal reasoning, model details, or private prompts.
