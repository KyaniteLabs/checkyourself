# Changelog

## Unreleased

The 2026-09-04/05 retrofit brought the local evidence contract through the
gauntlet, an ASTRA adversarial review, verifier-owned challenges, hardening, and
two independent final reviews. The documented boundary remains local evidence,
not production-safety certification or independent external custody.

### 2026-09-04 — Gauntlet waves 1–10

- Waves 1–7 hardened score trust, schema enforcement, scanner completeness and
  safe writes, backlog/diff semantics, malformed-input handling, proven versus
  merely detected evidence, and public validation. See [`WAVE1-REPORT.md`](_retrofit-2026-09-04/WAVE1-REPORT.md)
  through [`WAVE7-REPORT.md`](_retrofit-2026-09-04/WAVE7-REPORT.md).
- Waves 8–10 aligned public truth, current dogfood proof, and Apache-2.0
  license surfaces. See [`WAVE8-REPORT.md`](_retrofit-2026-09-04/WAVE8-REPORT.md),
  [`WAVE9-REPORT.md`](_retrofit-2026-09-04/WAVE9-REPORT.md), and [`WAVE10-REPORT.md`](_retrofit-2026-09-04/WAVE10-REPORT.md).

### 2026-09-04 — ASTRA adversarial review

- ASTRA found eight findings, including fabricated evidence credit, blanket
  non-applicability, residual-risk laundering, unknown/finding folding,
  unsupported report verdicts, broad discovery claims, and missing claim
  binding. The findings and executable repros are recorded in
  [`ASTRA-REVIEW.md`](_retrofit-2026-09-04/ASTRA-REVIEW.md).

### 2026-09-04 — ASTRA fixes and claim binding

- Closed the eight ASTRA findings with verifier-captured evidence, delegation
  receipts, residual-risk separation, independent unknown tracking, semantic
  report validation, and `--claim` evidence binding. Schema validity is now
  distinct from recomputed verdict consistency. See [`ASTRA-FIX-REPORT.md`](_retrofit-2026-09-04/ASTRA-FIX-REPORT.md).

### 2026-09-04 — Verifier-owned challenge runner

- Added the `challenge` verb and committed `.checkyourself/challenges.json`.
  Definitions use argv-only commands and bounded timeouts; failed and timed-out
  runs fail closed. Only successful verifier-executed `EXECUTED` receipts can
  receive full credit; caller-issued receipts are explicitly `UNVERIFIED` and
  capped. See [`CHALLENGE-RUNNER-REPORT.md`](_retrofit-2026-09-04/CHALLENGE-RUNNER-REPORT.md).

### 2026-09-05 — Runner hardening and semantic vacuity

- Score-time verification now re-executes stored receipts, binds each run with
  a project-local HMAC, and checks source, capture, exit, timeout, execution,
  and semantic output state. The HMAC is tamper evidence, not proof of
  independent issuance; external custody remains future work. See
  [`RUNNER-HARDEN-REPORT.md`](_retrofit-2026-09-04/RUNNER-HARDEN-REPORT.md).
- Verifier-owned per-surface minimum contracts reject or cap no-op, echo,
  print-only, hollow-runner, and trivial-regex challenges. See [`VACUITY-REPORT.md`](_retrofit-2026-09-04/VACUITY-REPORT.md).

### 2026-09-05 — Semantic re-execution normalization

- Fresh challenge runs now compare a semantic output digest that normalizes
  volatile durations, timestamps, and absolute paths while retaining raw capture
  hashing for tamper evidence. The final repository proof records 150 tests and
  88 subtests passed. See [`REEXEC-NORM-REPORT.md`](_retrofit-2026-09-04/REEXEC-NORM-REPORT.md).

### 2026-09-05 — Final independent green pair at `cd9cf85`

- Grok and Sol independently reviewed pinned `cd9cf85`; both reported fully
  green after ASTRA, challenge-runner, hardening, and normalization work. The
  receipts are [`FINAL-grok.md`](_retrofit-2026-09-04/FINAL-grok.md) and [`FINAL-sol.md`](_retrofit-2026-09-04/FINAL-sol.md).

### 2026-09-05 — Documentation and token-density passes

- Public docs updated across Forgejo and GitHub: README, `llms.txt`, and this
  changelog reflect the challenge runner, score-time re-execution, semantic
  vacuity rejection, local-integrity binding, `--claim` binding, and the ASTRA
  arc (see [`DOCS2-REPORT.md`](_retrofit-2026-09-04/DOCS2-REPORT.md)).
- Token-density pass (caveman + ponytail compression; protected-verbatim
  classes untouched), per [`DENSITY-PASS-REPORT.md`](_retrofit-2026-09-04/DENSITY-PASS-REPORT.md):

  | Scope | Before (chars / tokens) | After (chars / tokens) | Reduction |
  |---|---|---|---|
  | `skills/checkyourself/SKILL.md` | 9,236 / 2,368.2 | 7,330 / 1,879.5 | 20.6% |
  | `02_RUN_DIAGNOSTIC` | 13,110 / 3,361.5 | 10,379 / 2,661.3 | 20.8% |
  | `05_OUTPUT_TEMPLATES` | 17,845 / 4,575.6 | 14,213 / 3,644.4 | 20.4% |
  | `06_ADAPTERS` | 5,698 / 1,461.0 | 4,769 / 1,222.8 | 16.3% |
  | **Combined** | **45,889 / 11,766.4** | **36,691 / 9,407.9** | **20.0%** |

  Losslessness proven by the full verification chain after compression:
  150 tests + 88 subtests green; `tools/validate_public.py` green.
- Final landed state: verifier-executed challenges across 20 canonical
  surfaces and 10 scored categories; ASTRA 8/8 findings closed; final
  independent green pair (Grok-4.6 + Codex-SOL) at `cd9cf85`.

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
