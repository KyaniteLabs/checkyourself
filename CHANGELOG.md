# Changelog

## 1.6.3

- Calibrated env example detection so files like `.env.dogfood.example` are
  treated as examples, not real local `.env` files.
- Ignored commented secret placeholders and obvious example values for
  lower-confidence secret-like assignment findings, while preserving
  high-confidence credential-shape detection.

## 1.6.2

- Added reviewed finding suppressions through `.checkyourself.yml`, keeping
  suppressed findings visible in JSON while removing them from severity counts
  and score caps.
- Reduced false-positive P0 secret noise by separating high-confidence
  credential shapes from lower-confidence secret-like assignments, with line
  numbers, match type, confidence, and redacted context in evidence.
- Made `score` useful without coverage by returning a low-confidence
  scan-derived estimate, explicit `manual_evidence_needed`, and score history
  receipts in `.checkyourself-score-history.json`.
- Made `coverage --emit` write `CHECKYOURSELF_COVERAGE.generated.json` by
  default in text mode, while preserving JSON stdout for agent pipelines.
- Added the `diagnostic` alias, a starter `scan --deep` validation pass, and a
  composite GitHub Action for PR/CI usage.
- Added a field postmortem from real CheckYourself usage and updated CLI/MCP
  docs to match the shipped behavior.

## 1.6.1

- Redacted credential-shaped package script values before scan JSON or Markdown
  output, addressing the open PR review comment on script leakage.
- Added security and support docs plus a redacted bug-report issue template.
- Refreshed dogfood evidence to a 100/100 coverage-backed score for the current
  CLI/MCP public repo state.

## 1.6.0

- Promoted the CLI from scan-only helper to deterministic agent interface with
  `describe`, `scan`, `coverage`, `score`, `backlog`, `next`, `validate`,
  `schema`, `init`, and `mcp` commands.
- Added schema-backed contracts for scan, coverage, score, backlog, next batch,
  and capabilities.
- Added a zero-dependency stdio MCP wrapper over the same CLI functions.
- Expanded unit tests and CI smoke coverage for the agent-facing command
  surface.
- Updated CLI, MCP, README, manifest, and agent-access docs to match the
  shipped code instead of future-tense plans.

## 1.5.3

- Made the roast-lite reality-check voice part of the actual agent operating
  instructions, including `AGENTS.md`, the chat bootstrap, identity, and rules.
- Fixed workflow diagram callout alignment and regenerated the README image
  after visual verification.

## 1.5.2

- Reworked the README with a tighter product story, less process leak, and a
  clearer "check yourself before you wreck yourself" voice.
- Rebuilt the workflow diagram with sharper stage labels and Kyanite-style dark
  signal visuals.
- Replaced the dogfood dashboard preview with a fresh cache-busting screenshot
  filename.
- Updated user-facing docs to match the latest CLI, dashboard, language,
  accessibility, and product-personality behavior.

## 1.5.1

- Added the real dogfood dashboard screenshot to the README and refreshed the
  canonical dashboard styling with static, WCAG-friendly refinements.
- Added JSON stdout support for the optional local CLI via `--format json`,
  `--json -`, and `--json --no-write`.
- Added a small stdlib unit test suite for the CLI and wired it into GitHub
  Actions.
- Updated the validation workflow to current GitHub action majors and made the
  remote gitleaks scan install/run deterministically.
- Added the original agent-access CLI plan and decision record for the
  open-source product.
- Corrected the future scoring plan to be evidence-first instead of
  ready-until-proven-otherwise.

## 1.5.0

- Removed the beginner one-prompt-only path (`BEGINNER_PROMPT_ONLY.md`) and the
  `beginner_prompt` mode. CheckYourself is positioned as a complete staged
  system, not a single canned prompt.
- Reframed `PASTE_THIS_INTO_YOUR_AI.md` as the system bootstrap (operating
  instructions) for chat-only tools; file-aware tools start at `CONTEXT.md`.
- Added an optional local scan & scaffold CLI (`tools/checkyourself.py`,
  standard library only). It detects the stack, flags obvious deterministic
  issues (possible hardcoded secrets, missing `.env.example`, absent tests/CI),
  and writes a pre-filled context Markdown file plus JSON for the AI. Exit codes
  support a CI gate (`--ci`).
- Updated README, START_HERE, the start-here index, adapters, the advanced
  README, and the token-efficiency docs to remove one-prompt-path framing.

## 1.4.2

- Collapsed dashboard guidance to one canonical self-contained HTML/CSS
  dashboard and one compact inline Markdown fallback.
- Removed the older JavaScript/data-template dashboard fork and duplicate
  sample dashboard files.
- Redesigned the real dogfood dashboard using the KyaniteLabs black mineral
  instrument style, with cyan/magenta/amber signal roles.
- Added bilingual and neurodivergence-accessibility requirements for dashboard
  and learning-plan outputs.
- Added trusted YouTube video recommendations to learning priorities alongside
  written source links.

## 1.4.1

- Added a real CheckYourself dogfood report, recheck report, remediation log,
  learning-plan output, dashboard data, rendered dashboards, and dashboard
  screenshot proof.
- Fixed scanner-generated project-context output so it is ignored by default.
- Aligned manifest dashboard metadata with the dashboard docs.
- Expanded GitHub Actions with whitespace, Python compile, and
  gitleaks-if-available checks.
- Added a dogfood fixture for shallow-diagnostic regression checks.
- Added dashboard smoke-check guidance and cleaned Creator Kit path/version
  drift found by dogfooding.

## 1.4.0

- Added public repository validation with `tools/validate_public.py`.
- Added GitHub Actions validation for public repo health.
- Made the dashboard path explicit.
- Aligned the release boundary around the root public product plus private Creator Kit sidecar.
- Updated manifest and launch metadata for the public-ready repo shape.


## 1.3.0

- Clarified that CheckYourself performs a complete diagnostic and creates a complete remediation backlog.
- Added user-facing workflow diagram with no internal process leak.
- Added optional HTML/CSS dashboard mode and dashboard-data flow.
- Added token-efficiency guidance: dashboard off by default, advanced context loaded only when relevant.
- Added ICM-style context routing with stage-level `CONTEXT.md` files and output handoff folders.


## 1.2.0

- Added optional human-readable HTML/CSS dashboard mode.
- Added token-efficiency and progressive context-loading rules.
- Added user-facing workflow diagram with no internal process leak.
- Reinforced that the first approval batch is a safe starting batch, not the whole remediation scope.


## 1.1.0

- Clarified that CheckYourself must produce a complete remediation backlog, not just a small first approval batch.
- Renamed the beginner action list to “safest first approval batch.”
- Added a resolution policy: every finding must be fixed, accepted as risk, deferred with reason/date, or marked not applicable with evidence.
- Updated report schema with `remediation_backlog` and `first_approval_batch`.


## 1.0.0 — 2026-05-29

Initial public version of CheckYourself.

Includes:

- beginner prompt mode;
- folder-based diagnostic context;
- Production Reality Score;
- P0/P1/P2/P3 risk taxonomy;
- approval-based guided fix mode;
- bespoke learning-plan generator;
- full advanced production-hardening capability stack;
