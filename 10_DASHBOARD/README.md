# Optional Visual Dashboard

The dashboard is an optional HTML/CSS view of the CheckYourself report.

The default dashboard path is CSS-only:

- use `10_DASHBOARD/dashboard-template.html`;
- replace placeholders from the existing report;
- do not add JavaScript unless the user explicitly asks for a data-driven local
  template.

Use it when the user wants a visual, human-readable summary of:

- score;
- do-not-ship flags;
- P0/P1/P2/P3 counts;
- coverage status;
- complete remediation backlog;
- current approval batch;
- learning-plan priorities.

## Important

The dashboard is **not** the source of truth. The Markdown Production Reality Report is the source of truth because it is easier to diff, update, and keep token-efficient.

Only generate the dashboard when the user asks for it or includes:

```text
dashboard yes
```

Do not generate it by default.
