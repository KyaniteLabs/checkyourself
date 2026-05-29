# Token Efficiency

CheckYourself should be comprehensive without flooding the context window.

## Default rule

Do not load everything at once.

Load only what is needed for the current step.

## Recommended loading order

1. `CONTEXT.md` (file-aware tools) or `PASTE_THIS_INTO_YOUR_AI.md` (chat-only bootstrap)
2. `AGENTS.md`
3. `rules.md`
4. `02_RUN_DIAGNOSTIC/coverage-matrix.md`
5. `02_RUN_DIAGNOSTIC/scoring-method.md`
6. Output templates only when producing that output
7. Advanced capability files only when a specific domain needs them
8. Dashboard files only when the user asks for a dashboard

## Compact reporting rules

- Keep the full findings register complete but concise.
- Use stable finding IDs like `F-001`, `F-002`, `F-003`.
- Put expanded detail on P0/P1 findings and the next approval batch.
- Summarize P2/P3 items compactly unless the user asks for detail.
- Avoid repeating the same evidence in multiple sections.
- Do not paste long source files, logs, dependency trees, or references into the chat.
- Use “unknown” when evidence is missing instead of generating long speculative explanations.

## Dashboard rule

The dashboard is off by default.

Only generate the HTML/CSS dashboard when the user explicitly asks for it with wording like:

```text
dashboard yes
create a visual dashboard
```

The dashboard should summarize the existing report. It should not trigger a new audit.

If the user wants a dashboard-shaped summary without the HTML file, use:

```text
dashboard inline
```

That path returns the compact Markdown dashboard fallback.

## Never hide findings to save tokens

Token efficiency means compact representation, not incomplete auditing.

If there are 20 findings, keep all 20 in the register. Expand the highest-risk items first, then batch the rest.
