# Product

CheckYourself helps AI-assisted app builders inspect claimed work, expose
production risks, approve small fixes, and learn from the gaps. Its score is
bounded evidence, not a promise that an app is safe to launch
([README](README.md), [scoring method](02_RUN_DIAGNOSTIC/scoring-method.md)).

## Core experience

Start with [CONTEXT.md](CONTEXT.md) and the read-only diagnostic. Map the app,
sweep the coverage matrix, review a complete findings register and backlog,
approve fixes, recheck, and build a learning plan from actual findings. The
[guided-fix stage](03_GUIDED_FIX_MODE/README.md) requires approval; this is not an
autonomous production repair service. Language and accessibility rules live in
[AGENTS.md](AGENTS.md) and [rules.md](rules.md).

## What exists

- File-first context stages `00_START_HERE/`–`06_ADAPTERS/`, output templates in
  `05_OUTPUT_TEMPLATES/`, and deeper capability/reference guidance in
  `90_ADVANCED/` support assistants without a required model provider or account.
- A local Python CLI in `tools/checkyourself/` provides scan/diagnostic,
  coverage, challenge execution, evidence receipts, capped scoring, backlog,
  next-batch, diff and schema validation. `docs/cli.md` documents the interface;
  `schemas/` and `checkyourself.manifest.json` define machine contracts.
- Eleven stdio MCP tools wrap that same engine (`tools/checkyourself/mcp.py`,
  `docs/mcp.md`). The npm manifest identifies `@puenteworks/checkyourself`;
  `bin/checkyourself.mjs` launches Python. `Dockerfile` starts MCP as a non-root
  user. These are local interfaces, not a hosted dashboard or SaaS.
- `10_DASHBOARD/dashboard-template.html` is the opt-in self-contained dashboard;
  `10_DASHBOARD/inline-dashboard.md` provides a Markdown alternative.
  `index.html` is the public landing page, not the scanner application.
- `samples/` and committed stage `output/` artifacts provide worked examples.
  `reference/` and `90_ADVANCED/references/` contain guidance, not a hidden
  training corpus or externally validated benchmark dataset.

## Honest boundaries

Challenge commands execute on the user's host, including during receipt
revalidation at score time; they are not sandboxed and can access files or
networks. Project-local integrity bindings are not independent evidence custody
([architecture](ARCHITECTURE.md), `tools/checkyourself/receipts.py`). Keep private
reports and captures out of public commits; preserve [LICENSE](LICENSE) and
[NOTICE.md](NOTICE.md) when distributing. Do not interpret static discovery or
passing repository tests as a production-safety certification.

Native Hermes/Claude integrations proposed in open PRs are not default-branch
features. External evidence custody and other aspirations must remain labelled
planned until implemented and verified. Foundation and mirror proof limits are
tracked in [qa/foundation-gaps.md](qa/foundation-gaps.md).
