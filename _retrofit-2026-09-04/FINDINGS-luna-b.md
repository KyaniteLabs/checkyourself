# CheckYourself product-coherence findings

Verdict: `RETROFIT-NEEDED yes` — public documentation, machine contracts, and dated proof are not mutually consistent.

## Findings

### CYR-LUNA-B-001 — P1 — License claims conflict

- Evidence:
  - `README.md:7` — `[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)`
  - `README.md:268` — `Released under the MIT License.`
  - `checkyourself.manifest.json:5` — `"license": "Apache-2.0"`
  - `LICENSE:1` — `Apache License`
  - `NOTICE.md:5` — `It is released under the Apache License, Version 2.0.`
- Why it matters: Users, package indexes, and redistributors cannot determine the product's governing license from the public face.
- Fix sketch: Resolve the legal choice, then update README badge/text or manifest/LICENSE/NOTICE as one atomic change; rerun public validation.

### CYR-LUNA-B-002 — P2 — README dashboard image is broken

- Evidence:
  - `README.md:200` — dashboard image target was the missing
    `10_DASHBOARD/output/checkyourself-dogfood-dashboard-screenshot.png` file.
  - `10_DASHBOARD/output/` contains `checkyourself-dogfood-dashboard-live-20260612.png`, not the referenced `...screenshot.png`.
  - `tools/validate_public.py` reports: `broken local markdown link: README.md:200 -> 10_DASHBOARD/output/checkyourself-dogfood-dashboard-screenshot.png`.
- Why it matters: The primary visual proof does not render and the repository's public-validation test is red.
- Fix sketch: Point README at the intended existing artifact or add the intentionally named asset; rerun `validate_public.py` and the full test suite.

### CYR-LUNA-B-003 — P2 — README says MCP is future although it ships

- Evidence:
  - `README.md:190` — `...with MCP planned later as a thin native-agent wrapper.`
  - `docs/mcp.md:3` — `CheckYourself ships a local stdio MCP server.`
  - `checkyourself.manifest.json:19` — `"mcp_server"`
  - `tools/checkyourself.py:2581-2582` — parser registration for `mcp`.
- Why it matters: Agents and users can miss the shipped native interface or incorrectly treat it as unavailable.
- Fix sketch: Describe MCP as the current local thin wrapper, retain the no-hosted-API boundary, and remove the future-tense claim.

### CYR-LUNA-B-004 — P2 — README and FAQ contradict the shipped CLI

- Evidence:
  - `README.md:68` — `No model lock-in. No required cloud account. No command line.`
  - `README.md:185` — `python3 tools/checkyourself.py /path/to/your/project`
  - `README.md:188` — `The optional CLI supports explicit subcommands...`
  - `README.md:253` — `No build step, no dependencies, no CLI, and no cloud account.`
  - `START_HERE.md:27-35` — documents the local CLI and subcommands.
- Why it matters: The landing page and FAQ hide or deny the deterministic interface that agents are expected to use.
- Fix sketch: Change the claims to “no required command line” and “CLI optional,” then align the FAQ with START_HERE and `docs/cli.md`.

### CYR-LUNA-B-005 — P2 — llms.txt points detection-rule readers to the wrong file

- Evidence:
  - `llms.txt:14` — `rules.md — all detection rules with stable IDs (e.g. CY-SECRET-001) and severity levels`
  - `rules.md:1-23` — contains product behavior, voice, and safety rules, not the detector rule map.
  - `docs/cli.md:84-110` — contains the `CY-*` detector rule map and severities.
- Why it matters: LLM consumers following the index land on the wrong authority and may omit detector coverage or severity handling.
- Fix sketch: Describe `rules.md` as behavior/safety guidance and point detector-rule readers to `docs/cli.md` (or establish one canonical shared table).

### CYR-LUNA-B-006 — P2 — Agent-access plan still presents delivered work as proposed

- Evidence:
  - `docs/agent-access-cli-plan.md:3` — `Status: implemented in v1.6.0`
  - `docs/agent-access-cli-plan.md:171-173` — `## 5. Deterministic scoring algorithm (proposed)`
  - `docs/agent-access-cli-plan.md:280` — `## 9. MCP server (...) — Phase 3`
  - `docs/agent-access-cli-plan.md:298` — `The native server is now shipped...`
  - `docs/agent-access-cli-plan.md:329-338` — targets v1.6.0 and says all phases were delivered in v1.6.0.
  - `CHANGELOG.md:3` — `## 1.7.0 — 2026-06-12`
- Why it matters: Maintainers and agents cannot distinguish historical plan text from the current implemented contract.
- Fix sketch: Convert the document to an implemented decision record, archive proposed/phase language, and mark the current version/date explicitly.

### CYR-LUNA-B-007 — P2 — The plan permits a removed `blocked` status

- Evidence:
  - `docs/agent-access-cli-plan.md:123-124` — status includes `fixed / accepted-risk / deferred / blocked / not-applicable`.
  - `CHANGELOG.md:61-63` — `removed unschema’d statuses: verified, blocked, Scheduled`.
  - `03_GUIDED_FIX_MODE/README.md:57-65` — says `do not mark blocked`.
  - `schemas/checkyourself-report.schema.json:108-119` — status enum excludes `blocked`.
- Why it matters: An agent following the plan can emit a report that violates the current schema and guided-fix contract.
- Fix sketch: Remove `blocked` from the plan and specify the canonical `open` plus blocker/context note pattern.

### CYR-LUNA-B-008 — P2 — NotApplicable scoring math conflicts across canonical-looking docs

- Evidence:
  - `02_RUN_DIAGNOSTIC/scoring-method.md:22` — `NotApplicable gets full weight automatically, no redistribution.`
  - `docs/agent-access-cli-plan.md:218-221` — `NotApplicable categories are excluded from the denominator` and scores are normalized across applicable categories.
  - `tools/checkyourself.py:1450-1477` — implementation follows the full-weight/no-redistribution method.
- Why it matters: Hand-scored reports can disagree with the CLI, undermining score integrity and readiness claims.
- Fix sketch: Declare scoring-method plus CLI authoritative, update/archive the plan's alternate algorithm, and add a documentation-to-implementation consistency test.

### CYR-LUNA-B-009 — P2 — Complete-backlog template omits fields promised per backlog item

- Evidence:
  - `skills/checkyourself/SKILL.md:61-62` — each backlog item requires `why it matters` and `likely files/systems touched`.
  - `PASTE_THIS_INTO_YOUR_AI.md:61-63` — repeats those per-item requirements.
  - `05_OUTPUT_TEMPLATES/production-reality-report.md:111-116` — complete backlog table has no `Why it matters` or `Files likely touched` columns.
  - `05_OUTPUT_TEMPLATES/production-reality-report.md:118-132` — those fields appear only in the separate first-batch fix card.
- Why it matters: The promised complete remediation register can omit impact and scope for every item outside the first batch.
- Fix sketch: Add both columns to the complete backlog or require a per-item fix card block, then validate a generated report against the skill contract.

### CYR-LUNA-B-010 — P2 — Inline dashboard trigger is missing from template guidance

- Evidence:
  - `skills/checkyourself/SKILL.md:95-99` — supports `dashboard yes` and `dashboard inline`.
  - `START_HERE.md:57-63` — documents the inline fallback.
  - `05_OUTPUT_TEMPLATES/README.md:25` — `Do not generate dashboard unless user asks with “dashboard yes”.`
  - `10_DASHBOARD/README.md:43-47` — repeats only the `dashboard yes` trigger.
  - `checkyourself.manifest.json:89-92` — advertises `inline_markdown` mode.
- Why it matters: An agent reading the output-template entrypoint can ignore the supported low-token inline mode or choose the wrong output path.
- Fix sketch: Document both explicit triggers wherever dashboard generation is gated and keep the manifest trigger/mode language aligned.

### CYR-LUNA-B-011 — P2 — Security support policy is stale after tagged releases exist

- Evidence:
  - `SECURITY.md:7-9` — `The public main branch is the supported version until tagged releases begin.`
  - Repository tags include `v1.7.0` and `v1.4.2`.
  - `CHANGELOG.md:3` — `## 1.7.0 — 2026-06-12`.
- Why it matters: Security reporters are not told which released versions are supported now that tagged releases exist.
- Fix sketch: Replace the pre-release sentence with an explicit latest-release/main support policy and check it during release preparation.

### CYR-LUNA-B-012 — P1 — Dogfood receipts claim current passing state while current validation fails

- Evidence:
  - `02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-recheck-report.md:41-51` — records `100/100` and says `python3 tools/validate_public.py` passes.
  - `10_DASHBOARD/output/TASTECHECK-PASS.md:1` — `# TASTECHECK PASS — CheckYourself v1.7.0`.
  - `README.md:200` — references the now-missing dashboard image.
  - Current verification: `tools/validate_public.py` returns the broken README link; `pytest tests/ -q` returns `1 failed, 59 passed`.
- Why it matters: Historical proof is presented as current launch evidence despite a failing public gate, so consumers may trust an invalid readiness claim.
- Fix sketch: Regenerate receipts after fixing the public surface, or clearly label them historical; never advertise 100/100/current until validator and test evidence pass.

### CYR-LUNA-B-013 — P2 — Top-level CLI help hides the shipped subcommands

- Evidence:
  - `docs/cli.md:30-47` — documents `describe`, `scan`, `coverage`, `score`, `backlog`, `next`, `diff`, and `mcp`.
  - `tools/checkyourself.py:2509-2583` — defines the subcommand parser.
  - `tools/checkyourself.py:2596-2610` — routes an invocation beginning with `--help` through the legacy scan parser.
  - Current verification: `python3 tools/checkyourself.py --help` displays only the legacy positional-project options.
- Why it matters: A first-time agent or human using the conventional help command cannot discover the supported interface documented elsewhere.
- Fix sketch: Route top-level `--help` to the subcommand parser while preserving explicit legacy scan behavior, then test both help paths.

### CYR-LUNA-B-014 — P2 — Human coverage vocabulary drifts from the machine enum

- Evidence:
  - `02_RUN_DIAGNOSTIC/coverage-matrix.md:35-39` — exact statuses are `Pass`, `Finding`, `Unknown`, `NotApplicable`.
  - `docs/cli.md:186-194` — repeats `NotApplicable` as the machine status.
  - `05_OUTPUT_TEMPLATES/production-reality-report.md:63` — header says `Pass / Finding / Unknown / N/A`.
  - `02_RUN_DIAGNOSTIC/CONTEXT.md:26` — says `Pass/Finding/Unknown/N/A`.
- Why it matters: Readers and report generators can treat display shorthand as a schema value, producing inconsistent coverage records.
- Fix sketch: Use “Not applicable” in human-facing prose and reserve `NotApplicable` for JSON/CLI values; state that mapping once in the template.

## Coverage

- Swept public faces: `README.md`, `START_HERE.md`, `PASTE_THIS_INTO_YOUR_AI.md`, `llms.txt`, `identity.md`, `rules.md`.
- Swept numbered surfaces: `00-90` directories, with focused review of diagnostic, guided-fix, learning, dashboard, advanced, and output-template contracts.
- Swept agent contract and implementation: `skills/checkyourself/SKILL.md`, `docs/cli.md`, `docs/mcp.md`, `docs/agent-access-cli-plan.md`, `tools/checkyourself.py`.
- Swept machine metadata and schemas: `checkyourself.manifest.json`, `glama.json`, `MANIFEST.yaml`, report/coverage/learning/dashboard schemas, `CHANGELOG.md`.
- Swept dated/legal/support surfaces: dogfood reports and receipts, `SECURITY.md`, `LICENSE`, `NOTICE.md`, README release claims.
- Verification: manifest entrypoints all exist; manifest version `1.7.0` matches `CHANGELOG.md`; `describe --format json` succeeds; public validator fails on the README image; test suite reports `1 failed, 59 passed`.

## Passes and unknowns

- Pass: Manifest entrypoint paths, advertised dashboard template/fallback paths, version-to-changelog alignment, and advanced capability-directory count were internally consistent.
- Pass: `SKILL.md`, `rules.md`, guided-fix rules, and schema status enums generally agree on read-only operation, approval boundaries, and canonical lifecycle values except where findings above identify drift.
- Unknown: `glama.json` contains only schema and maintainer metadata; registry-side version/description behavior could not be verified offline.
- Unknown: Live Forgejo/GitHub publication and mirror state were not independently checked; this audit used the local repository as instructed.
