# Output Templates

These templates define what CheckYourself produces.

Default outputs are Markdown and should be compact, complete, and easy to scan.
The tone should be direct and useful: check yourself before you wreck yourself,
with evidence instead of vague reassurance.

## Default outputs

- `production-reality-report.md` — complete diagnostic report.
- `prioritized-fix-plan.md` — remediation backlog and fix order.
- `approval-card.md` — approval request before code/config changes.
- `bespoke-learning-plan.md` — custom learning path based on findings and fixes.
- `risk-register.md` — issue tracking format.
- `recheck-report.md` — after-fix verification report.

## Optional visual output

- `dashboard-output-instructions.md` — rules for when and how to generate it.
- `dashboard-prompt.md` — paste-ready prompt for requesting the dashboard.
- `dashboard-output.md` — expected dashboard output description.
- `dashboard-data.example.json` — sample data shape for the dashboard template.

Do not generate the dashboard unless the user explicitly asks with one of these
triggers:

- `dashboard yes` — create the canonical HTML/CSS dashboard;
- `dashboard inline` — return the compact Markdown dashboard fallback.

Use the single canonical dashboard path in `10_DASHBOARD/dashboard-template.html`.
If the user does not want HTML/CSS, use the inline Markdown fallback in
`10_DASHBOARD/inline-dashboard.md`. Canonical dashboard documentation lives in
`10_DASHBOARD/`; the files here are templates and pointers, not a second
dashboard system.
