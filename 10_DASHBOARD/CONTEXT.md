# Dashboard Stage Context

Use this stage only when the user explicitly asks for a visual dashboard after a
Production Reality Report exists. The CSS-only default dashboard path is
`10_DASHBOARD/dashboard-template.html`.

## Inputs

| Input | Required? | Notes |
|---|---|---|
| Production Reality Report | Yes | Do not re-run the audit just to build the dashboard. |
| Dashboard request | Yes | Canonical trigger: `dashboard yes`. |
| Current finding statuses | Preferred | Needed for progress display. |

## Process

1. Confirm the report exists.
2. Use `10_DASHBOARD/dashboard-template.html` for the CSS-only default.
3. Use `10_DASHBOARD/dashboard-data-contract.md` or the canonical dashboard
   schema selected by the repo.
4. Build a compact visual summary, not a replacement report.
5. Include the complete remediation backlog in compact form.
6. Keep it self-contained and free of external assets.

## Outputs

| Output | Where |
|---|---|
| Dashboard HTML | `10_DASHBOARD/output/CHECKYOURSELF_DASHBOARD.html` when file output is requested |
| Dashboard data | `10_DASHBOARD/output/dashboard-data.json` when data output is requested |

## Do Not

- Do not generate a dashboard during the first diagnostic by default.
- Do not include secrets, private data, long evidence dumps, external scripts,
  external fonts, trackers, or CDNs.
- Do not use the advanced JavaScript data-template path unless the user asks for
  dashboard data mode, an editable local template, or explicitly approves it.
