# Inline Dashboard Fallback

Use this when the user wants a dashboard-shaped summary but does not want a
self-contained HTML/CSS file.

Keep it short, complete, bilingual when needed, and easy to scan.

```markdown
## CheckYourself Dashboard Snapshot / Resumen

**Project / Proyecto:** {{PROJECT_NAME}}
**Score / Puntaje:** {{SCORE}}/100
**Confidence / Confianza:** {{CONFIDENCE}}
**Ship status / Estado para lanzar:** {{SHIP_STATUS}}

**One-line summary / Resumen corto:** {{SUMMARY}}

### Risk Counts / Conteo De Riesgos

| P0 | P1 | P2 | P3 | Unknown |
|---:|---:|---:|---:|---:|
| {{P0_COUNT}} | {{P1_COUNT}} | {{P2_COUNT}} | {{P3_COUNT}} | {{UNKNOWN_COUNT}} |

### Do-Not-Ship / No Lanzar Todavia

{{DO_NOT_SHIP_FLAGS}}

### Coverage Sweep / Cobertura

| Surface / Superficie | Status / Estado | Evidence / Evidencia |
|---|---|---|
{{COVERAGE_ROWS}}

### Complete Backlog / Lista Completa

| Order | Finding | Severity | Status | Next Step |
|---:|---|---|---|---|
{{BACKLOG_ROWS}}

### Learning Priorities / Prioridades De Aprendizaje

| Priority | Why It Matters | Do This Next | Source | YouTube |
|---|---|---|---|---|
{{LEARNING_ROWS}}

### Next Decision / Proxima Decision

{{NEXT_USER_DECISION}}
```

Rules:

- Keep the Markdown report as source of truth.
- Do not hide any finding to save tokens.
- Use finding IDs instead of repeating long evidence.
- Use plain language first, technical language second.
- If a user writes in Spanish, Spanish goes first and English supports technical terms.
- If another project language is detected, use that language first and keep English labels for common production terms.
