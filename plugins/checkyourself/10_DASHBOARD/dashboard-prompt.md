# Dashboard Prompt

Use this only after a Production Reality Report exists or when the user asks for a visual dashboard.

```text
Create an optional CheckYourself dashboard from the latest Production Reality Report.

Rules:
- Do not change code.
- Do not re-run the whole audit unless needed.
- Do not include secrets or sensitive values.
- If I ask for `dashboard yes`, use one self-contained `.html` file with inline CSS only.
- If I ask for `dashboard inline`, use the compact Markdown fallback instead.
- Do not use JavaScript.
- Do not create a second dashboard format.
- Keep the dashboard compact and human-readable.
- Make it accessible for ADHD, autism, and dyslexia: plain section labels, short sentences, stable layout, high contrast, and no motion-dependent meaning.
- Use English labels by default. If a second language is needed, ask the user to confirm before adding it to the dashboard.
- Show the complete remediation backlog, not only the first approval batch.
- Make clear that the first approval batch is only the safe starting point.
- Include a status for every finding using only the canonical values: `open`, `proposed`, `approved`, `fixed`, `accepted-risk`, `deferred`, `not-applicable`, or `suppressed`.

Sections to include:
1. Header with project name, date, score, and confidence.
2. P0/P1/P2/P3 count cards.
3. Do-not-ship flags.
4. Coverage sweep by production surface.
5. Complete remediation backlog.
6. Current approval batch.
7. Score explanation.
8. Learning plan snapshot.
9. Next user decision.
```
