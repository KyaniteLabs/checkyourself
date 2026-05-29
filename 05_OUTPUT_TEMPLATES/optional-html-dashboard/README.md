# Optional Human Audit Dashboard

The dashboard is a visual, human-readable HTML/CSS version of the CheckYourself report.

It is optional because it costs extra tokens.

The canonical template lives at `../../10_DASHBOARD/dashboard-template.html`.
This folder only keeps legacy generation notes.

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
- Do not include JavaScript.
- Do not rerun the audit just to make the dashboard.
- Keep evidence concise; link to paths instead of pasting long file contents.
- Include every finding, but keep rows compact.
- The dashboard is a visualization of the report, not a replacement for the report.
- Detect the primary language and candidate second language at runtime. If the
  second language is inferred rather than explicitly requested, ask before
  making labels bilingual.
- Preserve neurodivergent accessibility: stable sections, clear labels, high
  contrast, short paragraphs, and no motion-dependent meaning.

## Recommended output filename

```text
CHECKYOURSELF_DASHBOARD.html
```
