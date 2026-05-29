# Dashboard Stage Context

Use this stage only when the user explicitly asks for a visual dashboard or a
compact dashboard summary after a Production Reality Report exists. The
canonical HTML/CSS dashboard path is `10_DASHBOARD/dashboard-template.html`.
The inline Markdown fallback is `10_DASHBOARD/inline-dashboard.md`.

## Inputs

| Input | Required? | Notes |
|---|---|---|
| Production Reality Report | Yes | Do not re-run the audit just to build the dashboard. |
| Dashboard request | Yes | Canonical trigger: `dashboard yes`. |
| Current finding statuses | Preferred | Needed for progress display. |
| Language signals | Preferred | User prompt language, README/UI language, locale files, docs. |

## Process

1. Confirm the report exists.
2. Use `10_DASHBOARD/dashboard-template.html` for the single rich HTML/CSS dashboard.
3. If the user does not want HTML/CSS, use `10_DASHBOARD/inline-dashboard.md`.
4. Build a compact visual summary, not a replacement report.
5. Include the complete remediation backlog in compact form.
6. Keep it self-contained and free of external assets.
7. Detect the primary language and candidate second language at runtime.
8. If the second language is inferred rather than explicitly requested, ask the
   user before generating bilingual dashboard labels or learning blocks.
9. Preserve neurodivergent accessibility: plain labels, short text, high contrast,
   keyboard-readable structure, no flashing, and no information conveyed by color alone.

## Outputs

| Output | Where |
|---|---|
| Dashboard HTML | `10_DASHBOARD/output/CHECKYOURSELF_DASHBOARD.html` when file output is requested |
| Inline dashboard | Chat output or `10_DASHBOARD/output/CHECKYOURSELF_DASHBOARD.md` when low-token output is requested |
| Optional dashboard data | `10_DASHBOARD/output/dashboard-data.json` only when structured data is requested |

## Do Not

- Do not generate a dashboard during the first diagnostic by default.
- Do not include secrets, private data, long evidence dumps, external scripts,
  external fonts, trackers, or CDNs.
- Do not create a second JavaScript/data-template dashboard.
