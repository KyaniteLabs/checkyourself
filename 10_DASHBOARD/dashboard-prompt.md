# Dashboard Prompt

Use this only after a Production Reality Report exists or when the user asks for a visual dashboard.

```text
Create an optional CheckYourself HTML/CSS dashboard from the latest Production Reality Report.

Rules:
- Do not change code.
- Do not re-run the whole audit unless needed.
- Do not include secrets or sensitive values.
- Use one self-contained `.html` file.
- Use inline CSS only.
- Use no JavaScript unless I explicitly approve it.
- Keep the dashboard compact and human-readable.
- Show the complete remediation backlog, not only the first approval batch.
- Make clear that the first approval batch is only the safe starting point.
- Include a status for every finding: open, proposed, approved, fixed, verified, deferred, accepted-risk, or not-applicable.

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
