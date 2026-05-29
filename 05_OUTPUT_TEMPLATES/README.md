# Output Templates

These templates define what CheckYourself produces.

Default outputs are Markdown and should be compact, complete, and easy to scan.

## Default outputs

- `production-reality-report.md` — complete diagnostic report.
- `prioritized-fix-plan.md` — remediation backlog and fix order.
- `approval-card.md` — approval request before code/config changes.
- `bespoke-learning-plan.md` — custom learning path based on findings and fixes.
- `risk-register.md` — issue tracking format.
- `recheck-report.md` — after-fix verification report.

## Optional visual output

- `dashboard-output-instructions.md` — rules for when and how to generate it.

Do not generate the dashboard unless the user asks for it with `dashboard yes`.

Use the single canonical dashboard path in `10_DASHBOARD/dashboard-template.html`.
If the user does not want HTML/CSS, use the inline Markdown fallback in
`10_DASHBOARD/inline-dashboard.md`.
