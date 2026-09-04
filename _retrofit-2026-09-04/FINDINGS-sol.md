# Chief Auditor Findings — Systemic and Architecture

**RETROFIT-NEEDED: yes — the core CLI runs, but invalid evidence can receive a 100/high score, schema validation can accept garbage, prescribed read-only commands write files, and the regression gate misses replacement P0/P1 findings.**

## Findings

### CYR-SOL-001 — P0 — Invalid coverage can score 100 with high confidence

- **Promise:** `skills/checkyourself/SKILL.md:49-53` — “missing critical evidence at 84 ... absence of findings is treated as Unknown, never an automatic Pass” and coverage must be “Pass, Finding, Unknown, or Not applicable.”
- **Implementation:** `tools/checkyourself.py:1331-1340` accepts an arbitrary status into scoring; `tools/checkyourself.py:1452-1464` penalizes only `Unknown` and `MissingCoverage`; `tools/checkyourself.py:1522-1527` can then assign high confidence.
- **Reproduction:** all 20 canonical rows with `status: "Bogus"` make `coverage_check` fail, yet `score_from_inputs` returns `score=100`, `confidence=high`, `coverage_complete=true`, and no manual evidence needed.
- **Why it matters:** malformed or adversarial evidence can produce the strongest possible launch signal. The score is currently gameable at its trust boundary.
- **Fix sketch:** make `score` validate coverage first and fail closed; canonicalize IDs/categories/statuses; never award points or confidence for invalid rows. Add CLI and MCP regression tests for invalid, null, duplicate, unknown-ID, and mismatched-category rows.

### CYR-SOL-002 — P1 — The advertised read-only workflow silently mutates the audited project

- **Promise:** `skills/checkyourself/SKILL.md:19-20` — “Run deterministic checks when safe and available. Prefer read-only commands”; `skills/checkyourself/SKILL.md:86-87` — “Start read-only” and do not change code/config without approval. The prescribed commands are at `skills/checkyourself/SKILL.md:27-33`.
- **Implementation:** `tools/checkyourself.py:2025-2034` makes plain `coverage --emit` write `CHECKYOURSELF_COVERAGE.generated.json`; `tools/checkyourself.py:1919-1928` chooses a history path by default and `tools/checkyourself.py:2038-2049` appends score history for ordinary file input.
- **Why it matters:** an operator following the exact diagnostic recipe changes the target before approving a change. This breaks audit purity, dirties worktrees, and can alter later evidence.
- **Fix sketch:** make stdout/no-write the default for diagnostic verbs; require explicit `--out` and `--history` to persist. If backward compatibility is essential, change the skill to prescribe `coverage --format json` and `score --no-history`, and clearly label all write defaults.

### CYR-SOL-003 — P1 — `validate` does not implement the schemas it claims to validate

- **Promise:** `tools/checkyourself.py:1689-1692` says `validate` validates artifacts against bundled JSON schemas; `tools/checkyourself.py:2286-2304` exposes that promise to MCP.
- **Schema side:** `schemas/dashboard-data.schema.json:5-6` uses root `oneOf`; its two shapes require fields at `schemas/dashboard-data.schema.json:8-15` and `103-111`.
- **Implementation:** `tools/checkyourself.py:1813-1839` implements only `type`, `enum`, `required`, `properties`, `items`, `minimum`, and `maximum`; it ignores `oneOf`, `additionalProperties`, `minItems`, and other schema constraints.
- **Reproduction:** both `{}` and `{"garbage": true}` return `valid: true` for `--kind dashboard` logic.
- **Why it matters:** CI and agents receive a false proof of conformance. The dashboard contract is effectively unvalidated.
- **Fix sketch:** either implement every keyword used by bundled schemas (especially `oneOf`) or reject unsupported schema keywords at load time. Add a negative fixture for every schema and every supported combinator.

### CYR-SOL-004 — P1 — The report schema cannot prove the promised Production Reality Report

- **Promise:** `skills/checkyourself/SKILL.md:43-59` requires executive summary, app purpose, stack/confidence, unknowns, score rationale/caps, coverage, findings, evidence table, complete backlog, safest batch, diagnosis-changing questions, and learning seeds.
- **Schema side:** `schemas/checkyourself-report.schema.json:5-13` requires only `project`, `score`, `confidence`, `findings`, `remediation_backlog`, `first_approval_batch`, and `learning_plan_seeds`; `coverage` is optional at `schemas/checkyourself-report.schema.json:31-66`. It has no contract for executive summary, detected stack, unknowns/assumptions, score breakdown/caps, evidence table, full remediation path, or questions.
- **Reproduction:** a seven-field object with empty findings/backlog/learning arrays validates successfully as a report.
- **Why it matters:** `validate --kind report` can certify an artifact that omits most of the user-facing contract.
- **Fix sketch:** version and strengthen the report schema to represent every required section, require all 20 coverage surfaces or a linked validated coverage artifact, and add a golden valid report plus focused negative omissions.

### CYR-SOL-005 — P1 — `diff --ci` misses a new serious finding when the severity count stays flat

- **Promise:** `skills/checkyourself/SKILL.md:21-23` says stable IDs allow reliable diffs; `skills/checkyourself/SKILL.md:33` calls `diff --ci` the “regression gate.”
- **Implementation:** `tools/checkyourself.py:1592-1596` correctly identifies added/resolved IDs, but `tools/checkyourself.py:1626-1628` defines regression only as a net increase in aggregate open P0/P1 counts.
- **Reproduction:** replacing open P1 `A` with newly introduced open P1 `B` yields `added=[B]`, `resolved=[A]`, and `regression=false`; `--ci` exits zero.
- **Why it matters:** a new launch-blocking defect can enter while an unrelated defect closes, and CI reports no regression. Counts erase identity and risk-domain changes.
- **Fix sketch:** gate on any newly open P0/P1 ID, any re-opened P0/P1, and any severity escalation into P0/P1. Report these transitions explicitly; optionally retain a separately named net-count metric.

### CYR-SOL-006 — P1 — “Safest” backlog ordering is only lexical severity ordering

- **Promise:** `skills/checkyourself/SKILL.md:56-62` requires a complete ranked backlog and safest first approval batch with touched systems, verification, rollback, and learning value. `docs/agent-access-cli-plan.md:118-124` promises severity, reversibility/safety, and dependency ordering.
- **Implementation:** `tools/checkyourself.py:1546-1564` sorts only `(severity, category, finding_id)`; `tools/checkyourself.py:1632-1637` takes the first three at the top severity. No dependency, coupling, blast-radius, reversibility, or shared-file logic affects rank/batching.
- **Why it matters:** the CLI labels an arbitrary lexical slice “safest,” potentially separating coupled fixes or putting a destructive change ahead of a reversible prerequisite.
- **Fix sketch:** define explicit machine-readable safety/dependency fields, topologically order within severity, and batch only compatible/coupled items. Until implemented, rename output to `highest_severity_batch` and leave safest-batch selection to the report workflow.

### CYR-SOL-007 — P2 — Scan-derived coverage overstates tests and CI as Pass from file presence

- **Promise:** `skills/checkyourself/SKILL.md:36-38` limits scanner output to confirmed evidence; `skills/checkyourself/SKILL.md:89-90` says Pass requires evidence and forbids inflated scores.
- **Implementation:** `tools/checkyourself.py:1411-1415` marks C5 Pass when any test-like path is detected; `tools/checkyourself.py:1417-1421` marks C6 Pass when a CI filename exists. No test execution, assertion check, workflow parse, or success receipt is required.
- **Why it matters:** empty tests or a broken workflow become “Pass” evidence in `scan-derived-estimate`, even though presence proves only that files exist.
- **Fix sketch:** use `Detected`/`Unknown` for presence-only inference, or run/parse focused checks before Pass. Record test-run and CI validity receipts independently from discovery.

### CYR-SOL-008 — P2 — Coverage checking accepts structural drift

- **Promise:** `skills/checkyourself/SKILL.md:40-42` requires the whole production surface; `tools/checkyourself.py:1685-1686` says `coverage --check` validates completeness.
- **Implementation:** `tools/checkyourself.py:1167-1175` collapses rows into dictionaries and never rejects duplicate IDs/names; `tools/checkyourself.py:1174-1192` does not verify that a canonical ID retains its canonical surface and category.
- **Reproduction:** a complete matrix plus a duplicate S01 returns `complete=true`; changing every row’s category to C4 also returns `complete=true` (then scoring reports contradictory state).
- **Why it matters:** malformed evidence can pass the completeness gate and produce inconsistent scoring/category attribution.
- **Fix sketch:** require exactly 20 unique canonical IDs, exact ID/surface/category tuples, no duplicate names, and schema validity before semantic completeness checks.

### CYR-SOL-009 — P2 — Public documentation contradicts shipped MCP capability and contains a broken asset

- **Evidence:** `README.md:190` says MCP is “planned later”; `tools/checkyourself.py:2581-2582` ships the `mcp` command and `tools/checkyourself.py:2116-2323` exposes its tools. `README.md:198-200` claims a screenshot at `10_DASHBOARD/output/checkyourself-dogfood-dashboard-screenshot.png`, while the repository contains `checkyourself-dogfood-dashboard-live-20260612.png` instead.
- **Test receipt:** `python3 -m pytest tests/ -q` ran 60 tests plus 2 subtests: **59 passed, 1 failed, 2 subtests passed**. The failure is `ValidatePublicTests.test_real_repository_passes_validation` for the broken README link.
- **Why it matters:** the main product page understates a shipped interface and fails its own release validator.
- **Fix sketch:** update the MCP paragraph to current status; point the image at the existing canonical artifact (or deliberately rename it); keep the validator in required CI.

### CYR-SOL-010 — P2 — Adapter surface is legacy and does not match the product’s current native interfaces

- **Promise:** `06_ADAPTERS/README.md:3-9` says “Use the adapter that matches your environment” but lists only ChatGPT, Claude Projects, Cursor/Windsurf, Replit/Lovable/Bolt, and generic local agents.
- **Reality:** `tools/checkyourself.py:2116-2323` now exposes native MCP tools, and `tools/checkyourself.py:1679-1735` advertises CLI/MCP discovery. None of the adapters explains `describe`, MCP configuration, capability/schema discovery, restricted scan roots, or non-writing MCP behavior.
- **Why it matters:** current agent clients are routed through paste/upload-era instructions and may bypass the safest, deterministic interface.
- **Fix sketch:** add one canonical MCP/native-agent adapter and slim provider adapters to deltas; include Codex and modern ChatGPT/Claude/Cursor MCP paths without duplicating volatile setup details.

### CYR-SOL-011 — P2 — Promised test matrix is not implemented, so green tests would still be incomplete proof

- **Promise:** `docs/agent-access-cli-plan.md:314-323` calls for clean/secret/env/no-tests/AI fixtures, golden determinism, every scoring cap, redistribution, every emitted object’s schema conformance, a scan→score→validate CI pipeline, and no-secret output.
- **Existing tests:** `tests/test_checkyourself_cli.py:522-568` covers thin/full coverage scores; `tests/test_checkyourself_cli.py:570-587` covers only a net-count diff regression; `tests/test_checkyourself_cli.py:665-678` checks only positive diff conformance. There are no negative dashboard/report schema tests, invalid-coverage scoring tests, N/A scoring contract tests, equal-count replacement regressions, or deterministic golden snapshots. Static AST inspection found no test methods entirely lacking assertions.
- **Why it matters:** the highest-risk trust-boundary failures in findings 001–005 are outside the suite.
- **Fix sketch:** build table-driven contract tests around all CLI and MCP verbs, positive and negative schemas, all caps/status transitions, invalid evidence, mutation defaults, and stable golden outputs with timestamps normalized.

### CYR-SOL-012 — P3 — Scoring specifications disagree about NotApplicable math

- **Current scoring contract:** `02_RUN_DIAGNOSTIC/scoring-method.md:22` says a justified NotApplicable category receives full weight with no redistribution, matching `tools/checkyourself.py:1450-1477`.
- **Conflicting architecture document:** `docs/agent-access-cli-plan.md:218-221` says NotApplicable categories are excluded from the denominator and totals are normalized across applicable categories.
- **Why it matters:** two maintainers can implement different “correct” scores from repository-authoritative prose; external integrations cannot know which contract is stable.
- **Fix sketch:** designate `scoring-method.md` and `describe` as canonical, correct or archive the plan, and add an explicit NotApplicable scoring test and capability-manifest statement.

## Fix waves

1. **Wave 1 — Fail closed at trust boundaries (P0/P1):** fix coverage validation/scoring coupling (001), schema validation (003), and report schema (004). **Exit:** malformed coverage/dashboard/report artifacts fail in CLI and MCP; valid golden artifacts pass.
2. **Wave 2 — Restore safe workflow semantics (P1):** remove implicit diagnostic writes (002), make regression identity-aware (005), and stop calling lexical batches safest (006). **Exit:** prescribed audit commands leave git/files unchanged; transition matrix gates correctly; batch rationale is machine-verifiable.
3. **Wave 3 — Make evidence honest (P2):** downgrade presence-only Passes (007), enforce canonical coverage structure (008), and complete the contract test matrix (011). **Exit:** discovery cannot masquerade as executed proof; all advertised pipeline paths have positive and negative tests.
4. **Wave 4 — Align public architecture (P2/P3):** repair README/release validation (009), modernize adapters (010), and reconcile scoring prose (012). **Exit:** public validator and full test suite pass; README, adapters, manifest, capabilities, Docker/MCP docs, schemas, and canonical scoring docs agree.

## Coverage swept

- Skill promises: workflow, CLI recipe, stable rule IDs, score/caps, 20-surface report, backlog/approval loop, learning plan, safety rules, dashboard off/inline/HTML modes, and voice.
- CLI architecture: discovery and parser, scan/deep scan, suppression/status handling, coverage emit/check, scoring categories/penalties/caps/confidence, backlog/next, diff/CI gate, schema registry/validator, init/history writes, MCP tools/protocol/path confinement.
- Contracts: manifest, scan/coverage/score/backlog/next/diff/report/dashboard/capabilities schemas, production report, approval card, learning-plan template, inline and HTML dashboard documentation.
- Runtime/public surfaces: Dockerfile, glama metadata, README, START_HERE, bootstrap, llms, identity, rules, context, CLI/MCP docs, and all files in `06_ADAPTERS`.
- Tests: pytest primary runner, assertion-presence AST check, existing CLI/public-validator cases, and direct probes for invalid coverage, category drift, duplicate rows, schema garbage acceptance, P0 escalation/reopen, and equal-count P1 replacement.
- Docker/runtime review: stdlib-only imports, copied runtime paths, non-root user, stdio entrypoint, schema/manifest availability, and MCP scan-root confinement. No Docker daemon execution was attempted.

## Unknowns

- Container build/start behavior was statically reviewed but not built; Docker availability and registry pull access were not established and network use was prohibited.
- No coverage profiler is configured, so line/branch coverage percentage is unknown; behavioral gaps above are based on test inventory and focused reproductions.
- Provider UI setup changes over time; the adapter finding establishes missing native-interface coverage, not exact current vendor UI steps (network prohibited).

## IMPROVEMENTS

1. **Make one executable contract test the release spine.** Why: skill, schema, CLI, and public docs drifted independently. Proposal: generate capability assertions and golden artifacts from canonical constants, then run scan→coverage-check→score→backlog→next→diff→validate through both CLI and MCP.
2. **Separate observation from persistence.** Why: audit commands silently write coverage/history. Proposal: make every diagnostic verb stdout/read-only by default and require an explicit `--write`/`--out` destination for artifacts.
3. **Add negative fixtures before feature fixtures.** Why: happy-path conformance passed while garbage dashboards and invalid evidence were accepted. Proposal: maintain a compact rejection corpus for every schema, status transition, and evidence-integrity boundary.
