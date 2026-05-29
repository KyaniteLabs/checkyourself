# Diagnostic Prompt

```text
Use CheckYourself diagnostic mode.

Inspect the project read-only.

Create a Production Reality Report using the template in 05_OUTPUT_TEMPLATES/production-reality-report.md.

Requirements:
- Infer the stack from evidence.
- Separate evidence from assumptions.
- Use 02_RUN_DIAGNOSTIC/coverage-matrix.md and cover every relevant production surface as Pass, Finding, Unknown, or Not applicable.
- Rank issues P0/P1/P2/P3.
- Apply the scoring method in 02_RUN_DIAGNOSTIC/scoring-method.md.
- Explain each issue in plain English first.
- Detect the user's language and project language from prompts, docs, UI strings, and locale files. If the user or project is not English-only, make learning/dashboard outputs bilingual.
- Keep explanations accessible for ADHD, autism, and dyslexia: short sections, concrete next actions, stable labels, and no dense walls of text.
- Build a complete findings register and remediation backlog for every finding and blocking unknown.
- Recommend a safest first approval batch from that backlog. Do not imply the first batch is the whole fix scope.
- Be token efficient: compact tables for broad coverage, detailed fix cards only for the next approval batch.
- Do not modify files.
- Do not generate the HTML dashboard unless the user says dashboard yes.
- End by offering guided fix mode, optional dashboard mode, optional inline dashboard fallback, and a bespoke learning plan.
```
