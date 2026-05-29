# Optional Human Audit Dashboard

The dashboard is a visual, human-readable HTML/CSS version of the CheckYourself report.

It is optional because it costs extra tokens.

## When to generate it

Only generate the dashboard when the user explicitly says:

```text
dashboard yes
```

## What it should show

- Production Reality Score.
- Ship status.
- P0/P1/P2/P3 counts.
- Coverage sweep.
- Complete findings register.
- Complete remediation backlog.
- Current approval batch.
- Resolution progress.
- Bespoke learning-plan highlights.

## Rules

- Use a single self-contained HTML file.
- Use inline CSS.
- Do not use external dependencies.
- Do not include JavaScript unless the user asks.
- Do not rerun the audit just to make the dashboard.
- Keep evidence concise; link to paths instead of pasting long file contents.
- Include every finding, but keep rows compact.
- The dashboard is a visualization of the report, not a replacement for the report.

## Recommended output filename

```text
CHECKYOURSELF_DASHBOARD.html
```
