# Dashboard Smoke Check

Use this after generating a CheckYourself dashboard from a real Production
Reality Report.

## Minimum checks

1. Open the generated dashboard HTML in a browser.
2. Confirm the score, confidence, generated date, and project name are visible.
3. Confirm P0/P1/P2/P3 counts match the source report.
4. Confirm every coverage row is represented.
5. Confirm the complete remediation backlog is present, not only the first batch.
6. Confirm the first approval batch is visibly labeled as the next safe step.
7. Confirm the learning-plan snapshot is visible.
8. Confirm no external scripts, fonts, trackers, or CDNs are loaded.

## Optional screenshot proof

If browser automation is available, save a screenshot next to the dashboard in
`10_DASHBOARD/output/` and keep it out of source templates unless the user asks
to publish it.
