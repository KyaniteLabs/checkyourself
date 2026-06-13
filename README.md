<p align="center">
  <img src="assets/checkyourself-hero.webp" alt="checkyourself — local-first production-readiness audit for AI-built apps" width="100%">
</p>

# CheckYourself

> **Check yourself before you wreck yourself.** A pre-launch reality check for AI-built apps.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Version 1.7.0](https://img.shields.io/badge/version-1.7.0-blue.svg)](CHANGELOG.md)
[![Model-agnostic](https://img.shields.io/badge/AI-model--agnostic-blue.svg)](#works-with-your-ai-tool)
[![Read-only first](https://img.shields.io/badge/safety-read--only%20first-brightgreen.svg)](#safety-model)
[![Zero dependencies](https://img.shields.io/badge/python-stdlib%20only-black.svg)](#local-cli-and-mcp)
[![MCP ready](https://img.shields.io/badge/MCP-ready-black.svg)](docs/mcp.md)

CheckYourself turns your AI assistant into a pre-launch production reviewer. Point it at your project, ask for a read-only diagnostic, and get a scored, evidence-backed report of what will break when real users, data, and deploys show up — before they do.

It maps your app, checks the places AI-built projects usually get humbled, gives you a 0-100 Production Reality Score, ranks every finding, suggests the safest first fixes, and builds a learning plan from the exact gaps in your project.

It is not a linter with a clipboard. It is not a shame machine. It is a calm, evidence-first second opinion with just enough side-eye to keep your launch honest.

**No SaaS. No account. No model lock-in. No telemetry. No code changes unless you approve them.**

## Why CheckYourself, not just "review my app"

Asking your AI to "review my app" gives you a different answer every time and stops after the first three obvious things. CheckYourself makes the audit *repeatable and hard to fake*:

- **Complete, not shallow.** A 20-surface coverage sweep that refuses to stop at the first few findings — every surface ends as Pass, Finding, Unknown, or Not-applicable, with evidence.
- **A score you can't game.** Severity caps keep real risk from hiding behind polish, missing evidence counts as Unknown (never an automatic pass), and an estimate can never report a launch-ready number. [How the score works.](docs/checkyourself-score-explained.md)
- **Stable, citable findings.** Every deterministic finding has a fixed rule ID (`CY-SECRET-001`, `CY-CONFIG-001`, …) so you can suppress it, track it, and gate CI on it across runs.
- **Regression-aware.** `diff` compares two runs and fails CI when new P0/P1 risk appears — so you gate on *what changed*, not just an absolute count.
- **Local-first and inspectable.** Plain Markdown plus a zero-dependency Python CLI. Nothing leaves your machine; secret values are redacted before they ever reach output.

## Quick Start

Get the folder (clone it as a sibling of your project, or copy it in):

```bash
git clone https://github.com/KyaniteLabs/checkyourself.git
```

Kick the tires read-only in one command — no dependencies, nothing leaves your machine:

```bash
python3 checkyourself/tools/checkyourself.py scan /path/to/your/project
```

For the full diagnostic, point your AI coding assistant at [`CONTEXT.md`](CONTEXT.md) and use this prompt:

```text
Use the checkyourself folder as your operating context.
Start with a read-only diagnostic.
Do not change code until I approve a specific fix.
Generate the dashboard only if I say dashboard yes.
After the diagnostic, create a learning plan based on the gaps you found.
```

Then: review the score, findings, backlog, and safest first fix batch → approve fixes one batch at a time → recheck, rescore, and learn what to avoid next time.

## What a check looks like

You get a plain-English report, not a wall of lint. Here is the shape of it:

```text
Production Reality Score: 49 / 100   (one unresolved P0 caps the score at 49)

P0 — fix before launch
  CY-SECRET-001  High-confidence credential shape in source
                 A live-looking key sits in the repo. Rotate it, move it to env,
                 and confirm it is not in git history.
  [auth]         No proof of server-side ownership checks
                 A logged-in user may read another user's record by changing an ID.
                 Add a tenant/owner check and a negative test.

P1 — fix soon
  CY-TEST-001    No automated tests detected
  CY-ENV-003     No .env.example for required configuration

P2 — fix when you can
  CY-CI-001      No CI pipeline detected

Safest first fix batch: CY-SECRET-001  (reversible, high-impact, with verification)
```

Deterministic detector findings carry stable `CY-` IDs you can suppress and gate
on; findings that need your AI's judgment (like the `[auth]` one above) are
tagged by surface instead. Then it ranks the full backlog, proposes a small
approval-ready first batch with verification and rollback notes, and — once you
approve — fixes, re-verifies, and rescores. See a full example in
[`samples/sample-production-reality-report.md`](samples/sample-production-reality-report.md).

## How It Works

![CheckYourself workflow: map the app, check reality, pick the safest fix, verify receipts, learn what to avoid next time, then recheck before launch](assets/checkyourself-user-workflow.png)

CheckYourself moves in a loop:

1. **Map the app** - infer what it is, who it serves, and what stack it uses.
2. **Check reality** - sweep the production risk surfaces with evidence.
3. **Pick the safest fix** - rank the backlog by harm, reversibility, and learning value.
4. **Verify the receipts** - run the checks that prove the fix actually helped.
5. **Learn what to avoid next time** - turn the gaps into a practical learning plan.

Then it rechecks before launch, because vibes are not a deployment strategy.

## What You Get

- **Production Reality Report** - plain-English diagnosis, detected stack, score, unknowns, findings, evidence, and backlog.
- **Production Reality Score** - 0-100, with severity caps so serious risk cannot hide behind nice polish.
- **Complete Findings Register** - not just the first three obvious problems.
- **Safest First Fix Batch** - a small approval-ready batch with verification and rollback notes.
- **Guided Fix Loop** - approve, fix, verify, rescore, repeat.
- **Bespoke Learning Plan** - practical next lessons tied to your actual app, with trusted sources and relevant videos when available.
- **Optional Dashboard** - a self-contained HTML/CSS view, or a compact inline Markdown version when tokens matter.

See a sample report in [`samples/sample-production-reality-report.md`](samples/sample-production-reality-report.md).

## Dashboard Preview

CheckYourself audits itself. This is the real dogfood dashboard from that self-audit — a coverage-backed **100 / 100**, earned under the same caps and evidence rules it holds your app to (and re-earned under v1.7.0's stricter, harder-to-game scoring):

![CheckYourself dogfood dashboard showing the self-audit score, launch status, risk counts, and coverage sweep](10_DASHBOARD/output/checkyourself-dogfood-dashboard-live-20260529.png)

The dashboard is optional. The Markdown report stays the source of truth because it is cheaper, easier to diff, and easier for agents to update.

To request the visual dashboard after a report exists:

```text
dashboard yes
```

For the lower-token version:

```text
dashboard inline
```

Dashboard docs live in [`10_DASHBOARD/`](10_DASHBOARD/README.md).

## What It Checks

CheckYourself looks for launch trouble across the surfaces that matter:

- product purpose, users, and harm model;
- frontend UX, accessibility, and client safety;
- backend/API behavior, validation, uploads, and webhooks;
- auth, permissions, sessions, roles, and admin paths;
- data storage, migrations, backups, and tenant/user isolation;
- secrets, environment variables, and runtime configuration;
- tests, quality gates, and regression coverage;
- CI/CD, dependencies, supply chain, and release safety;
- deployment, rollback, hosting, and environments;
- observability, logs, errors, alerts, and incident response;
- performance, scaling, caching, and rate limits;
- privacy, compliance, retention, and consent;
- AI/RAG/agent governance when applicable.

The optional CLI also runs **deterministic detectors** with stable rule IDs so the cheap, high-signal footguns get caught the same way every time: committed secrets and `.env` files, debug flags left on, default or weak credentials, wildcard CORS, dangerous code sinks, shipped source maps, missing lockfiles, unpinned CI actions, and untested payment or LLM integrations. Reviewed false positives can be suppressed in `.checkyourself.yml` without silencing the rest.

The advanced hardening library is in [`90_ADVANCED/`](90_ADVANCED/). You do not need to read it first; agents load it only when a finding needs deeper guidance.

## Works With Your AI Tool

CheckYourself is plain Markdown plus a small optional Python CLI, so it works with tools that can read text or project files:

| Category | Examples |
| --- | --- |
| AI IDEs and editors | Cursor, Windsurf, GitHub Copilot, Codex |
| Chat assistants | ChatGPT, Claude, Gemini |
| App builders | Replit, Lovable, Bolt |
| Local and custom agents | any local model or agent that reads files |

Tool-specific setup guides live in [`06_ADAPTERS/`](06_ADAPTERS/README.md).

## Claude And Codex Skill

CheckYourself also ships as an installable agent skill at [`skills/checkyourself/SKILL.md`](skills/checkyourself/SKILL.md).

Use this path when submitting CheckYourself to Claude/Codex skill aggregators, or when installing it as a reusable production-readiness audit workflow. The skill preserves the same safety model: read-only first, complete coverage sweep, evidence-backed score, safest first fix batch, and optional dashboard only on request.

## Local CLI And MCP

The folder workflow is the main product. The CLI is the deterministic engine for agents, CI, and local receipts:

```bash
python3 tools/checkyourself.py /path/to/your/project
```

It detects stack signals, flags obvious deterministic risks (each finding carries a stable rule ID like `CY-SECRET-001` for reliable CI gating), writes a prefilled context file, emits schemas, checks coverage, computes the score, records score history, ranks the backlog, and exposes a thin MCP wrapper. The `diff` command compares two scan results to surface regressions and track progress over time:

```bash
python3 tools/checkyourself.py describe --format json
python3 tools/checkyourself.py scan . --format json --no-write
python3 tools/checkyourself.py diagnostic . --format json --no-write
python3 tools/checkyourself.py scan . --deep --format json --no-write
python3 tools/checkyourself.py coverage --emit
python3 tools/checkyourself.py score --findings CHECKYOURSELF_SCAN.generated.json --format json
python3 tools/checkyourself.py scan . --ci
python3 tools/checkyourself.py diff --old baseline.json --new current.json --ci
python3 tools/checkyourself.py mcp
```

The CLI does not replace the full diagnostic. It handles deterministic work so your AI can spend its attention on judgment. Scan-only scores are clearly marked as low-confidence estimates; coverage-backed scores require filled evidence.

Reviewed false positives can be suppressed in `.checkyourself.yml`, and suppressed findings remain visible in JSON without counting against caps. That means the tool can learn from real projects without forcing cosmetic renames just to appease a regex with an attitude problem.

For CI, use the included composite action at
`.github/actions/checkyourself`. It runs the scan, validates the JSON contract,
and can fail pull requests on unresolved P0 findings.

Read [`docs/cli.md`](docs/cli.md) for the command reference and [`docs/mcp.md`](docs/mcp.md) for MCP setup. There is no hosted API unless CheckYourself becomes a service product with accounts, shared history, hosted runs, or billing.

## Personality

CheckYourself has a point of view:

- **Receipts over reassurance.** A pass needs evidence.
- **Roast-lite agent voice.** The side-eye is built into `AGENTS.md` and the chat bootstrap: one sharp reality check, then evidence, impact, fix, verification.
- **Small fixes beat heroic rewrites.** The safest batch goes first.
- **Learning is part of the product.** If your app had the gap, your plan explains the gap.
- **Accessible by default.** Short sections, literal labels, high contrast, no motion-dependent meaning, and runtime language support when the user wants it.
- **The checker learns from receipts.** Real remediation postmortems become durable agent rules when they expose a gap.

The vibe is: a launch coach, a security-minded friend, and a code reviewer who knows when to say, "Not yet. Here is why."

Recent agent self-improvement notes live in [`docs/agent-self-improvement.md`](docs/agent-self-improvement.md).

## Safety Model

CheckYourself starts read-only.

It inspects, explains, ranks, and recommends before touching code. Fixes require explicit approval, stay small and reversible, include verification, and update the score only after evidence changes.

For regulated, financial, health, legal, life-safety, security-critical, or high-volume systems, CheckYourself should recommend qualified expert review. It is a strong pre-launch pass, not a substitute for professional accountability.

## Support And Security

Use [SUPPORT.md](SUPPORT.md) for bugs, docs gaps, CLI/MCP problems, accessibility issues, and stale examples.

Use [SECURITY.md](SECURITY.md) for vulnerability handling. Do not post live secrets, customer data, proprietary code, or unredacted `.env` values in public issues.

## FAQ

### Is CheckYourself a prompt?

No. It includes prompts, but the product is a staged audit workspace: rules, context files, scoring, templates, schemas, examples, dashboard support, an optional CLI, and an advanced hardening library.

### Do I need the command line?

No. The CLI is optional. File-aware AI tools can start at [`CONTEXT.md`](CONTEXT.md). Chat-only tools can use [`PASTE_THIS_INTO_YOUR_AI.md`](PASTE_THIS_INTO_YOUR_AI.md).

### Is it free?

Yes. CheckYourself is Apache 2.0 licensed.

### Is it affiliated with any specific AI model or IDE?

No. It is model-agnostic and tool-agnostic.

### How is it different from a linter?

Linters catch style and narrow code issues. CheckYourself asks whether the app is actually ready to face users, data, auth, deploys, failures, privacy, and production pressure.

### How is it different from just asking my AI to review my app?

See [Why CheckYourself](#why-checkyourself-not-just-review-my-app) above. Short version: a staged workflow turns a one-off opinion into a repeatable, gateable receipt.

### Does it work in CI?

Yes. The composite action at `.github/actions/checkyourself` runs the scan, validates the JSON contract, and can fail pull requests on unresolved P0 findings. Use `diff --ci` to fail only on *new* P0/P1 risk against a baseline.

## Contributing

Issues and pull requests are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CHANGELOG.md`](CHANGELOG.md).

## License

Apache 2.0. See [`LICENSE`](LICENSE).

---

## Part of KyaniteLabs

More from [KyaniteLabs](https://kyanitelabs.tech). Related projects:

- **[devarch-framework](https://github.com/KyaniteLabs/devarch-framework)** — git-repository archaeology framework
- **[dev-learning-archaeologist](https://github.com/KyaniteLabs/dev-learning-archaeologist)** — forensic git-history learning diagnostic
- **[Epoch](https://github.com/KyaniteLabs/Epoch)** — time-estimation MCP server (PERT) for AI agents

→ More at **[kyanitelabs.tech](https://kyanitelabs.tech)**
