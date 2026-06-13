# Changelog

## 1.7.0 — 2026-06-12

Major reliability, security, and detection-depth pass.

### Detection

- Gave every scan finding a **stable, semantic rule ID** (`CY-SECRET-001`,
  `CY-CONFIG-001`, …) instead of position-dependent `CY-NNN` numbers, so
  suppressions, diffs, and CI gates stay valid across runs and releases.
- Added deterministic detectors: debug flags in committed config
  (`CY-CONFIG-001`), default/weak credentials (`CY-CONFIG-002`), CORS wildcard
  (`CY-API-001`), dangerous code sinks — eval, unsafe deserialization, disabled
  TLS, raw HTML injection (`CY-CODE-001`), production source maps (`CY-WEB-001`),
  missing lockfile (`CY-SUPPLY-002`), `npm install` in CI (`CY-SUPPLY-004`), and
  untested LLM integrations (`CY-AI-001`).
- Expanded secret scanning to more config formats (`.tf`, `.tfvars`,
  `.properties`, `.ini`, `.cfg`, `.conf`, `.xml`, `.vue`, `.svelte`, and more)
  and made the secret regexes share one credential-name token list so detection
  and redaction can never drift apart.
- Fixed a false negative where the secret scanner stopped after the first
  high- and low-confidence hit, missing later credentials in the same file.
- Reduced false positives: risk-surface path hints and test/doc-path skips now
  match whole path segments instead of substrings (`docker-compose.yml` is no
  longer treated as a doc, `user-agent.ts` no longer flags as an AI agent path).

### Scoring integrity

- Closed a scoring-gaming vector: a coverage artifact that omits surfaces or
  marks them `Pass`/`NotApplicable` without evidence can no longer reach a
  perfect, high-confidence score. Omitted surfaces count as `Unknown`, thin
  `Pass` entries downgrade to `Unknown`, and `confidence: "high"` requires all
  20 surfaces present with real evidence.
- Evidence caps (84/90) now apply in every score mode, so estimates can never
  report a launch-ready number. A scan finding no secrets is treated as absence
  of evidence (`Unknown`), not proof of safe handling (`Pass`).

### New capability

- Added a `diff` command and MCP tool: compare two findings artifacts and report
  added, resolved, and regressed findings, with a `regression` flag and `--ci`
  gate so CI can block *new* P0/P1 risk instead of only absolute counts.

### Security

- The scanner no longer follows symlinks or reads files outside the scanned
  tree; skipped symlinks and unreadable files are disclosed in `scan_limits`.
- Large scans now disclose truncation (`scan_limits.truncated`, configurable via
  `--max-files`) instead of silently returning a partial result.
- MCP scans are confined to `CHECKYOURSELF_SCAN_ROOT`, and unknown/misspelled
  tool arguments and tool names are rejected rather than silently ignored.
- The composite GitHub Action passes inputs through environment variables to
  remove a script-injection sink; the Dockerfile runs as a non-root user with a
  `.dockerignore`; Dependabot now covers the Docker ecosystem.
- Generated files are never written through a symlink, and a corrupt score
  history file is preserved as `.corrupt.bak` rather than silently overwritten.

### Documentation and content

- Canonicalized the finding resolution-status vocabulary across every doc to
  the report-schema set (now including `suppressed`); removed the unschema'd
  `verified`, `blocked`, and `Scheduled` statuses.
- Deepened the advanced hardening references with 2026-current, checkable
  guidance: AI/RAG and agent governance (prompt injection, PII in traces,
  token-cost controls, output validation), privacy (DSAR/erasure mechanics,
  consent, breach timelines), deployment (edge/serverless gotchas, platform
  config checks), and API hardening (webhook signatures, idempotency).
- Fixed all 38 capability-file reference pointers to resolve from their actual
  location, expanded `llms.txt` into a real link map, wired the orphaned
  `identity.md`/`examples.md`/`reference/` files into the context router, added
  a deterministic-receipts step to the diagnostic stage, and removed the legacy
  `optional-html-dashboard` folder that v1.4.2 had already claimed to remove.
- Made the dashboard bilingual behavior ask-first, matching the repo-wide rule.
- Refreshed the dogfood receipts: the self-audit now scores 100/100 under the
  stricter v1.7.0 anti-gaming rules, with one reviewed, path-scoped
  suppression documented in `.checkyourself.yml`.

### Fixes and housekeeping

- Score-history timestamps are UTC for cross-machine comparability; scoring from
  stdin no longer litters the working directory with a history file.
- Retired the unused `dashboard-html` schema (the `dashboard-data` schema's
  `oneOf` already covers the template mode) and added a `diff` schema.
- Hardened `validate_public.py` against non-dict samples, added directory
  ignores and a size cap, and gave it its own test suite.
- Aligned `NOTICE.md` and reference docs with the Apache-2.0 license.

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
