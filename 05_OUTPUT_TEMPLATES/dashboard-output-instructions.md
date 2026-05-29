# Optional Human Dashboard Instructions

The dashboard is optional because it costs extra tokens.

Generate the HTML/CSS dashboard only when the user explicitly asks for it, or when the user sets:

```text
dashboard yes
```

Use `10_DASHBOARD/dashboard-template.html` for the default CSS-only dashboard.
Use `05_OUTPUT_TEMPLATES/checkyourself-dashboard.html` only for the advanced
data-template path when the user asks for dashboard data mode or approves
JavaScript.

## Rules

- Do not generate the dashboard by default.
- Do not include secret values, tokens, private keys, personal data, or long code blocks.
- Keep the dashboard as a visual summary of the report, not a duplicate of every detail.
- Use finding IDs to avoid repeating long explanations.
- Include the complete remediation backlog in compact table form.
- Show the safest next approval batch, but make clear the backlog continues after that batch.
- Use one self-contained HTML file with inline CSS and no external assets.
- Prefer short sentences and plain language.
- If the report is very large, summarize P2/P3 rows compactly and offer a second dashboard page only if the user asks.
