# CheckYourself

**Before you ship it, CheckYourself.**

CheckYourself is a model-agnostic production-readiness diagnostic, guided remediation, optional visual dashboard, and bespoke learning-plan system for AI-built apps.

It helps your AI assistant inspect an app, infer the stack, find production gaps, explain the risks in plain English, propose fixes for approval, verify the fixes, and generate a learning plan based on what your own project was missing.

It is also organized as an ICM-style context workspace: [`CONTEXT.md`](CONTEXT.md) routes the agent to staged folders, each major stage has its own `CONTEXT.md`, and durable handoff artifacts belong in stage `output/` folders. CheckYourself is not affiliated with the RinDig ICM project; it uses the same file-first idea so agents know what to read, do, and produce at each step.

---

## TL;DR

```text
Add the folder → run the audit → review the full backlog → approve fixes → verify → repeat → learn what you missed
```

CheckYourself is not a “top three issues” tool. It creates a complete findings register and a complete remediation backlog. The first approval batch is intentionally small so fixes stay safe, understandable, and reversible.

---

## The 60-second version

1. Download or clone this folder.
2. Put `checkyourself` in or next to your project.
3. Open your AI coding assistant.
4. Paste [`PASTE_THIS_INTO_YOUR_AI.md`](PASTE_THIS_INTO_YOUR_AI.md).
5. Review the Production Reality Report.
6. Approve fixes one at a time or in safe batches.
7. Recheck and rescore after each batch.
8. Continue until every finding is fixed, deferred with a reason, accepted as risk, blocked by missing context, or proven not applicable.
9. Get a custom learning plan based on the actual gaps.

No model lock-in. No required cloud account. No command line required.

---

## Visual workflow

![CheckYourself user workflow](assets/checkyourself-user-workflow.png)

---

## What this produces

Default outputs:

- **Project Map** — what your app appears to do.
- **Detected Stack** — framework, database, auth, hosting, tests, deployment signals, and confidence.
- **Production Reality Score** — a 0–100 score with caps and reasoning.
- **Coverage Sweep** — every relevant production surface marked Pass, Finding, Unknown, or Not applicable.
- **Complete Findings Register** — every discovered risk, not just the obvious ones.
- **Complete Remediation Backlog** — every finding and blocking unknown ranked by severity, safety, and dependency order.
- **Safest First Approval Batch** — the first reversible batch to approve, not the whole scope.
- **Guided Fix Loop** — approve, fix, verify, rescore, repeat.
- **Bespoke Learning Plan** — what to learn next based on what your own app was missing.

Optional output:

- **Human Audit Dashboard** — a self-contained HTML/CSS dashboard that visualizes the score, risks, backlog, coverage, status, and learning plan. It is optional because dashboards use extra tokens. Ask for it with `dashboard yes`.

---

## Who this is for

CheckYourself is for people who build with AI and want reality before production does the grading:

- beginners learning by doing;
- intermediate builders who can ship but want a safer second pass;
- experienced developers who want a reusable audit context;
- AI-built app learners and community builders;
- Cursor, Windsurf, Replit, Lovable, Bolt, ChatGPT, Claude, Gemini, Codex, and local-agent users;
- founders, freelancers, agencies, and teams preparing real launches.

---

## What it checks

The diagnostic should sweep the whole relevant production surface:

- product purpose, users, and harm model;
- frontend UX, accessibility, and client safety;
- API/backend behavior, validation, uploads, and webhooks;
- auth, permissions, sessions, roles, and admin paths;
- data storage, migrations, backups, and tenant/user isolation;
- secrets, environment variables, and runtime configuration;
- tests, quality gates, and regression coverage;
- CI/CD, supply chain, dependencies, and release safety;
- deployment, rollback, hosting, and environments;
- observability, logs, errors, alerts, and incident response;
- performance, scaling, caching, and rate limits;
- privacy, compliance, data retention, and consent;
- AI/RAG/agent governance when applicable.

The full technical engine lives in [`90_ADVANCED/`](90_ADVANCED/), but users do not need to read it first.

---

## Quick start: easiest path

Open [`PASTE_THIS_INTO_YOUR_AI.md`](PASTE_THIS_INTO_YOUR_AI.md), copy the prompt, and give it to your AI assistant with your project.

For the absolute simplest version, use [`BEGINNER_PROMPT_ONLY.md`](BEGINNER_PROMPT_ONLY.md).

If your AI coding tool understands folder context, start at [`CONTEXT.md`](CONTEXT.md). It routes the tool to the right stage without loading the whole repo.

---

## Quick start: folder path

If your AI coding tool can read project files, put this folder inside or next to your repo and say:

```text
Use the checkyourself folder as your operating context.
Start with a read-only diagnostic.
Do not make code changes until I approve a specific fix.
Generate the dashboard only if I say dashboard yes.
After the diagnostic, create a learning plan based on the gaps you found.
```

---

## Optional Human Audit Dashboard

The Markdown report is the default output because it is cheaper, faster, and easier for most AI tools to produce.

After the report exists, say:

```text
dashboard yes
```

The AI should create a single self-contained HTML/CSS dashboard from the report. It should not re-run the audit just to make the dashboard.

Dashboard files:

- [`10_DASHBOARD/README.md`](10_DASHBOARD/README.md)
- [`10_DASHBOARD/dashboard-data-contract.md`](10_DASHBOARD/dashboard-data-contract.md)
- [`10_DASHBOARD/dashboard-prompt.md`](10_DASHBOARD/dashboard-prompt.md)
- [`10_DASHBOARD/dashboard-template.html`](10_DASHBOARD/dashboard-template.html)

---

## Token efficiency by design

CheckYourself uses progressive context loading:

- Start with the short prompt and coverage matrix.
- Load advanced files only when a domain is relevant.
- Keep the complete findings register compact.
- Expand details for P0/P1 items and the next approval batch.
- Do not paste long source files, logs, or reference docs back to the user.
- Generate the HTML dashboard only when the user asks for it.

See [`docs/token-efficiency.md`](docs/token-efficiency.md).

---

## The most important safety rule

Start read-only.

CheckYourself should inspect, explain, and recommend before any code or config changes happen. Fixes require explicit user approval.

---

## License

MIT License. See [`LICENSE`](LICENSE).
