# Optional Dashboard Mode

The dashboard is optional because generating HTML can use extra tokens.

## Default behavior

Do **not** generate an HTML dashboard during the first diagnostic unless the user explicitly asks for one.

During the default diagnostic, produce:

1. the Markdown Production Reality Report;
2. the complete remediation backlog;
3. the learning-plan seeds;
4. a short offer: “I can also generate the optional HTML dashboard or a compact inline dashboard.”

## When the user asks for the dashboard

Prefer the lowest-token path that matches the user's request:

Use the single canonical HTML/CSS dashboard for rich visual output. Use the
inline Markdown fallback when the user wants dashboard-shaped output without an
HTML file.

### Single canonical HTML/CSS dashboard

1. Copy `10_DASHBOARD/dashboard-template.html` to `10_DASHBOARD/output/CHECKYOURSELF_DASHBOARD.html` or another user-approved output path.
2. Replace the placeholders from the existing Production Reality Report.
3. Do not add JavaScript.
4. Use this when the user asks for `dashboard yes`, a visual dashboard, or an HTML report.

### Inline Markdown fallback

1. Use `10_DASHBOARD/inline-dashboard.md`.
2. Return it in chat or write it to `10_DASHBOARD/output/CHECKYOURSELF_DASHBOARD.md`.
3. Use this when the user asks for `dashboard inline`, declines HTML/CSS, or needs the most token-efficient dashboard-shaped output.

### Best path in chat-only mode

Return either:

1. the inline Markdown dashboard if the user wants compact output; or
2. one self-contained HTML/CSS file if the user specifically asks for the full dashboard file.

## Dashboard data rules

The dashboard must visualize:

- Production Reality Score;
- P0/P1/P2/P3 counts;
- Do-not-ship flags;
- coverage sweep;
- complete remediation backlog;
- fix progress/status;
- bespoke learning plan with plain-English next actions and live source/video
  links for each priority.
- bilingual labels/content when the user or codebase is not English-only.
- neurodivergence-accessible structure: short sections, predictable labels,
  high contrast, no flashing, and no information conveyed by color alone.

The dashboard must not replace the full report. It is a visual companion.

## Token control

- Do not paste long source files into the dashboard.
- Summarize evidence as paths and short observations.
- Use finding IDs instead of repeating full explanations everywhere.
- Keep data compact; expand details only when the user asks.
