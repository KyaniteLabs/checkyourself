# Optional HTML Dashboard Output

The dashboard is optional. Default behavior is **no dashboard** to save context and tokens.

Use it only when the user asks for a visual dashboard, HTML output, or a more readable summary.

## Modes

- `DASHBOARD=off` — default. Produce the Markdown report only.
- `DASHBOARD=data` — produce compact dashboard JSON only.
- `DASHBOARD=html` — produce one self-contained HTML/CSS dashboard after the report. Use this only if the user explicitly wants the AI to write the HTML.

For HTML output, default to the CSS-only template in `10_DASHBOARD/`. Use
`05_OUTPUT_TEMPLATES/checkyourself-dashboard.html` only as the advanced local
data-template path when the user asks for dashboard data mode, wants an editable
template, or explicitly approves JavaScript.

## Dashboard rule

The dashboard is a visual summary, not a replacement for the full report.

The full Production Reality Report and complete remediation backlog remain the source of truth.

## What to show

A useful dashboard should show:

1. app name and detected stack;
2. Production Reality Score and confidence;
3. P0/P1/P2/P3 counts;
4. do-not-ship blockers;
5. coverage status by production surface;
6. complete findings table, using compact finding IDs;
7. remediation waves and current next approval request;
8. learning-plan priorities.

## Token-efficiency constraints

- Do not generate HTML unless requested.
- Do not duplicate every paragraph from the report.
- Keep explanations short and link them to finding IDs.
- If generating HTML directly, keep it self-contained, CSS-only, and concise.
- No external scripts, no external fonts, no remote images, and no analytics.

## No process leak

The dashboard should explain the user workflow and findings. Do not expose internal reasoning, hidden chain-of-thought, model-specific implementation details, or private prompt mechanics.
