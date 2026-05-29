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

- `optional-human-dashboard.html` — self-contained HTML/CSS dashboard.
- `dashboard-output-instructions.md` — rules for when and how to generate it.
- `checkyourself-dashboard.html` — advanced local data-template dashboard that
  replaces embedded JSON and uses inline JavaScript.

Do not generate the dashboard unless the user asks for it with `dashboard yes`.

Default to the CSS-only dashboard path in `10_DASHBOARD/`. Use the advanced
data-template dashboard only when the user asks for dashboard data mode, an
editable local template, or explicitly approves JavaScript.
