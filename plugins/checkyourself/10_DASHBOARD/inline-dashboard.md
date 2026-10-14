# Inline Dashboard Fallback

Use this when the user wants a dashboard-shaped summary but does not want a
self-contained HTML/CSS file.

Keep it short, complete, bilingual only after the user requests or confirms the
second language, and easy to scan.

```markdown
## {{DASHBOARD_SNAPSHOT_LABEL}}

**{{PROJECT_LABEL}}:** {{PROJECT_NAME}}
**{{SCORE_LABEL}}:** {{SCORE}}/100
**{{CONFIDENCE_LABEL}}:** {{CONFIDENCE}}
**{{SHIP_STATUS_LABEL}}:** {{SHIP_STATUS}}

**{{SUMMARY_LABEL}}:** {{SUMMARY}}

### {{RISK_COUNTS_LABEL}}

| P0 | P1 | P2 | P3 | Unknown |
|---:|---:|---:|---:|---:|
| {{P0_COUNT}} | {{P1_COUNT}} | {{P2_COUNT}} | {{P3_COUNT}} | {{UNKNOWN_COUNT}} |

### {{DO_NOT_SHIP_LABEL}}

{{DO_NOT_SHIP_FLAGS}}

### {{COVERAGE_LABEL}}

| {{SURFACE_LABEL}} | {{STATUS_LABEL}} | {{EVIDENCE_LABEL}} |
|---|---|---|
{{COVERAGE_ROWS}}

### {{BACKLOG_LABEL}}

| Order | Finding | Severity | Status | Next Step |
|---:|---|---|---|---|
{{BACKLOG_ROWS}}

### {{LEARNING_PRIORITIES_LABEL}}

| Priority | Why It Matters | Do This Next | Source | YouTube |
|---|---|---|---|---|
{{LEARNING_ROWS}}

### {{NEXT_DECISION_LABEL}}

{{NEXT_USER_DECISION}}
```

Rules:

- Keep the Markdown report as source of truth.
- Do not hide any finding to save tokens.
- Use finding IDs instead of repeating long evidence.
- Use plain language first, technical language second.
- Detect primary language and candidate second language at runtime.
- If a second language is inferred from locale, audience, region, docs, or UI strings, ask the user before using it.
- Fill the `*_LABEL` placeholders with primary-language labels, or bilingual labels after explicit user choice.
