# Beginner Prompt Only

Use this when you do not want to deal with folders, scripts, repos, or setup.

```text
I built an app and I want you to CheckYourself it before I ship it.

Please act as a friendly production-readiness reviewer.

Start read-only. Do not change code until I approve a specific fix.

First, ask me only the few questions you need to understand the app. Then create a simple report with:

1. What you think my app does.
2. What stack/tools you think I used.
3. A broad sweep of the production areas that could matter: auth, data, secrets, APIs, frontend, tests, deployment, observability, performance, privacy, and AI features if present.
4. The biggest things that could go wrong if real users use it.
5. A score from 0 to 100, explained clearly.
6. A complete ranked issue list and remediation backlog, not just a few fixes.
7. The safest first approval batch and why it comes first.
8. The full path to keep fixing until every issue is fixed, deferred with a reason, accepted as risk, or proven not applicable.
9. A learning plan for me based on what I missed and what remediation was needed.

Please be token efficient: do not paste huge files back to me, do not generate a dashboard unless I ask for it, and explain things like I am smart but may not know the vocabulary yet.

If I say “dashboard yes,” create a simple self-contained HTML/CSS dashboard from the report so I can see the score, findings, backlog, and learning plan visually.
```
