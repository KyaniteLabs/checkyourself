# Optional Dashboard Mode

HTML uses extra tokens. Do **not** generate it during the first diagnostic
without an explicit request. Default output is the Markdown report, complete
backlog, learning-plan seeds, and: "I can also generate the optional HTML
dashboard or a compact inline dashboard."

## Requested dashboard

Use the single canonical HTML/CSS dashboard for rich output; use the inline Markdown fallback for dashboard-shaped output without HTML.

### Single canonical HTML/CSS dashboard

1. Copy `10_DASHBOARD/dashboard-template.html` to
   `10_DASHBOARD/output/CHECKYOURSELF_DASHBOARD.html` or another user-approved
   output path.
2. Replace placeholders from the existing Production Reality Report.
3. Do not add JavaScript.
4. Use for `dashboard yes`, a visual dashboard, or an HTML report.

### Inline Markdown fallback

1. Use `10_DASHBOARD/inline-dashboard.md`.
2. Return it in chat or write it to
   `10_DASHBOARD/output/CHECKYOURSELF_DASHBOARD.md`.
3. Use for `dashboard inline`, declined HTML/CSS, or the lowest-token path.

In chat-only mode, return the inline fallback for compact output; return one
self-contained HTML/CSS file only when the user requests the full file.

## Dashboard data rules

Visualize Production Reality Score; P0/P1/P2/P3 counts; do-not-ship flags;
coverage; complete backlog; fix progress/status; and bespoke learning with
plain-English actions plus live source/video links for each priority. Bilingual
labels/content require an explicit second-language request or confirmed
inferred candidate. Use short, predictable, high-contrast sections; no flashing
or color-only meaning; clear risk calls without shame or roast. The dashboard
is a visual companion, not the full report.

## Token control

Summarize evidence as paths and short observations; use finding IDs instead of
repeated explanations; expand only on request.
