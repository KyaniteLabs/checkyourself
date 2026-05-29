# Optional Dashboard Mode

The dashboard is optional because generating HTML can use extra tokens.

## Default behavior

Do **not** generate an HTML dashboard during the first diagnostic unless the user explicitly asks for one.

During the default diagnostic, produce:

1. the Markdown Production Reality Report;
2. the complete remediation backlog;
3. the learning-plan seeds;
4. a short offer: “I can also generate the optional HTML dashboard.”

## When the user asks for the dashboard

Prefer the lowest-token path that works in the current environment:

### Default CSS-only path

1. Copy `10_DASHBOARD/dashboard-template.html` to `10_DASHBOARD/output/CHECKYOURSELF_DASHBOARD.html` or another user-approved output path.
2. Replace the placeholders from the existing Production Reality Report.
3. Do not add JavaScript.

### Advanced data-template path when files can be edited

This is the advanced data-template path.

1. Copy `05_OUTPUT_TEMPLATES/checkyourself-dashboard.html` to `CHECKYOURSELF_DASHBOARD.html`.
2. Replace only the JSON inside `<script id="checkyourself-data" type="application/json">`.
3. Use this path only when the user asks for dashboard data mode, wants an
   editable local template, or explicitly approves JavaScript.
4. Do not rewrite the whole HTML template unless necessary.

### Best path in chat-only mode

Return either:

1. a compact JSON object matching `dashboard-data.example.json`, if the user has the template; or
2. one self-contained HTML file if the user specifically asks for the full dashboard file.

## Dashboard data rules

The dashboard must visualize:

- Production Reality Score;
- P0/P1/P2/P3 counts;
- Do-not-ship flags;
- coverage sweep;
- complete remediation backlog;
- fix progress/status;
- bespoke learning plan.

The dashboard must not replace the full report. It is a visual companion.

## Token control

- Do not paste long source files into the dashboard.
- Summarize evidence as paths and short observations.
- Use finding IDs instead of repeating full explanations everywhere.
- Keep data compact; expand details only when the user asks.
