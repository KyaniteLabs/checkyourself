# Dashboard Generation Prompt

```text
Generate the optional CheckYourself Human Audit Dashboard.

Use the existing Production Reality Report and remediation status. Do not re-run the audit.

Create one self-contained HTML file named CHECKYOURSELF_DASHBOARD.html using
`10_DASHBOARD/dashboard-template.html`.

Requirements:
- Inline CSS only.
- No external fonts, scripts, CDNs, trackers, or images.
- No JavaScript.
- Show score, ship status, severity counts, coverage status, complete findings register, complete remediation backlog, current approval batch, and learning-plan highlights.
- Include every finding, but keep rows compact.
- Use plain English labels.
- Include the user's language when the prompt or codebase is not English-only.
- Keep the layout accessible for ADHD, autism, and dyslexia.
- Mark unresolved P0/P1 clearly.
- Show resolution statuses: open, approved, fixed, deferred, accepted-risk, not-applicable.
- Do not paste raw source files or secret values.
```
