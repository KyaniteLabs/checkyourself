# Optional Human Dashboard Instructions

Generate only when the user asks or sets:

```text
dashboard yes
```

Use `10_DASHBOARD/dashboard-template.html` for the single canonical HTML/CSS
dashboard. If the user does not want HTML/CSS, use
`10_DASHBOARD/inline-dashboard.md`.

## Rules

- Never generate by default.
- Exclude secrets, tokens, private keys, personal data, and long code.
- Summarize with finding IDs; include the complete backlog and safest next
  approval batch, and show the backlog continues.
- HTML: one self-contained file, inline CSS, no external assets.
- Use short, plain sentences. Detect primary/candidate second language at
  runtime; if inferred, ask before bilingual labels or learning sections.
- Support ADHD, autism, and dyslexia: predictable structure/spacing, high
  contrast, no flashing, and text labels beyond color.
- Compact P2/P3 rows; offer another page only on request.
