# Optional Visual Dashboard

The dashboard is an optional visual view of the CheckYourself report. It should
feel like a launch instrument panel: opinionated, high-contrast, calm, and a
little bit pointed.

There is one rich visual dashboard path:

- use `10_DASHBOARD/dashboard-template.html`;
- replace placeholders from the existing report;
- do not add JavaScript, external fonts, trackers, remote images, or CDNs.

There is also one token-efficient fallback:

- use `10_DASHBOARD/inline-dashboard.md`;
- return it in chat or a Markdown file;
- use it when the user does not want HTML/CSS or when context budget matters.

Use it when the user wants a visual, human-readable summary of:

- score;
- do-not-ship flags;
- P0/P1/P2/P3 counts;
- coverage status;
- complete remediation backlog;
- current approval batch;
- learning-plan priorities.

The dashboard must be usable by neurodivergent readers: clear sections,
literal labels, high contrast, short paragraphs, stable tables, and no
motion-dependent meaning. Detect the primary language and candidate second
language at runtime. Include a second language only when the user explicitly
requests it or confirms the inferred candidate.

Voice guidance: useful side-eye is welcome; mean-spirited roasting is not. The
dashboard can say "not ready yet" clearly, but it must also show the next safest
move.

## Important

The dashboard is **not** the source of truth. The Markdown Production Reality Report is the source of truth because it is easier to diff, update, and keep token-efficient.

Only generate the dashboard when the user asks for it or includes:

```text
dashboard yes
```

Do not generate it by default.
