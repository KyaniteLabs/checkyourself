# CheckYourself Master Register

## Synthesis rules

- Severity is the highest substantiated impact when reproductions disagree; corroboration without an independent reproduction does not raise severity.
- `FINDINGS-floor-lfm.md` contains no completed review, so it contributes no findings.
- The fresh-eyes claim that no scanner or tests exist is contradicted by `FINDINGS-sol.md`, `FINDINGS-luna-a.md`, and `FINDINGS-luna-b.md`, which inspected and exercised both. It is dropped. Its warning about self-certified proof is retained in MR-012 because current validation independently failed.
- Two instruction-only concerns are retained as **CONTENDED** at P3: reviewers found ambiguity, but the implementation audits did not demonstrate a runtime defect.

## Merged findings

| ID | Title | Severity consensus | Corroborating voices | Strongest file:line evidence | Fix sketch |
|---|---|---:|---|---|---|
| MR-001 | Invalid coverage can score 100 with high confidence | P0 | `FINDINGS-sol.md`, `FINDINGS-luna-a.md` | `tools/checkyourself.py:1331-1340,1452-1464,1522-1527` | Validate canonical coverage before scoring; reject invalid/null/duplicate/unknown/mismatched rows in CLI and MCP; never award confidence for invalid evidence. |
| MR-002 | Diagnostic commands silently mutate the audited project | P1 | `FINDINGS-sol.md` | `tools/checkyourself.py:1919-1928,2025-2049`; `skills/checkyourself/SKILL.md:27-33,86-87` | Make stdout/no-history the default and require explicit `--out` or `--history` for persistence; regression-test a clean-tree audit. |
| MR-003 | Bundled schema validator ignores `oneOf` and other used keywords | P1 | `FINDINGS-sol.md`, `FINDINGS-luna-a.md` | `tools/checkyourself.py:1813-1839`; `schemas/dashboard-data.schema.json:5-15,103-111` | Use a standards-complete validator or fail closed on unsupported keywords; add a negative fixture per schema/combinator. |
| MR-004 | Report schema certifies artifacts missing most promised report sections | P1 | `FINDINGS-sol.md` | `skills/checkyourself/SKILL.md:43-59`; `schemas/checkyourself-report.schema.json:5-13,31-66` | Version and strengthen the schema to require the report contract, including canonical coverage or a validated linked artifact; add golden and omission tests. |
| MR-005 | `diff --ci` misses newly opened serious findings when counts stay flat | P1 | `FINDINGS-sol.md` | `tools/checkyourself.py:1592-1596,1626-1628` | Gate on newly open/reopened/escalated P0/P1 identities, not net aggregate counts; expose transitions separately. |
| MR-006 | “Safest” batch is only lexical severity ordering | P1 | `FINDINGS-sol.md`, `FINDINGS-floor-crack.md`, `FINDINGS-floor-champion.md` | `tools/checkyourself.py:1546-1564,1632-1637`; `docs/agent-access-cli-plan.md:118-124` | Add explicit dependency, reversibility, coupling, and blast-radius fields with topological batching; until then rename it `highest_severity_batch`. |
| MR-007 | Unreadable, oversized, and truncated files look clean | P1 | `FINDINGS-luna-a.md` | `tools/checkyourself.py:294-302,477-480,614` | Record every skipped/read-failed/truncated file and mark the scan incomplete; scan eligible content fully or disclose limits. |
| MR-008 | Extensionless configuration files bypass content detectors | P1 | `FINDINGS-luna-a.md` | `tools/checkyourself.py:612-614` | Include known basenames such as Dockerfile, Makefile, and Jenkinsfile in applicable content detectors. |
| MR-009 | Ordinary filenames are misclassified as automated tests | P1 | `FINDINGS-luna-a.md`; related evidence in `FINDINGS-sol.md` | `tools/checkyourself.py:669-676` | Match path components and established test filename patterns instead of arbitrary substrings. |
| MR-010 | Output writes can escape through symlinked parent directories | P1 | `FINDINGS-luna-a.md` | `tools/checkyourself.py:1881-1889` | Resolve and validate every parent beneath the intended root, or use directory-fd/O_NOFOLLOW atomic writes. |
| MR-011 | Public license claims conflict | P1 | `FINDINGS-luna-b.md` | `README.md:7,268`; `checkyourself.manifest.json:5`; `LICENSE:1`; `NOTICE.md:5` | Obtain the owner’s legal choice, then align README, manifest, LICENSE, and NOTICE atomically. |
| MR-012 | Dogfood receipts claim a current pass while current validation fails | P1 | `FINDINGS-luna-b.md`, `FINDINGS-sol.md`, `FINDINGS-dsv4.md` | `02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-recheck-report.md:41-51`; `10_DASHBOARD/output/TASTECHECK-PASS.md:1`; `README.md:200` | Fix the failing public surface, regenerate receipts from current evidence, and label immutable old receipts historical. |
| MR-013 | Non-object `package.json` crashes scan | P2 | `FINDINGS-luna-a.md` | `tools/checkyourself.py:505-509` | Type-check parsed JSON and return a stable shape finding or CLI input error without traceback. |
| MR-014 | Invalid suppression configuration is silently discarded | P2 | `FINDINGS-luna-a.md` | `tools/checkyourself.py:394-405,1001-1002` | Surface `config_error` and fail closed with a stable configuration finding or input error. |
| MR-015 | `.gitignore` handling uses substring checks instead of pattern semantics | P2 | `FINDINGS-luna-a.md` | `tools/checkyourself.py:533-535,749-750,845` | Parse comments and gitignore patterns, then evaluate paths with anchored, directory-aware semantics. |
| MR-016 | Recognized env-example variants still trigger the missing-example finding | P2 | `FINDINGS-luna-a.md` | `tools/checkyourself.py:538-543,864-865` | Reuse `is_env_example_name` as the single classification source. |
| MR-017 | `diff` misses status-only resolutions | P2 | `FINDINGS-luna-a.md` | `tools/checkyourself.py:1592-1596` | Treat open-to-resolved status changes as resolutions and report all other status transitions separately. |
| MR-018 | Coverage checking crashes on non-object JSON | P2 | `FINDINGS-luna-a.md` | `tools/checkyourself.py:1160-1165` | Validate the root type before `.get` and return a structured incomplete result or exit-code-2 input error. |
| MR-019 | MCP coerces invalid argument types instead of rejecting them | P2 | `FINDINGS-luna-a.md` | `tools/checkyourself.py:2175-2186,2359-2361` | Validate values against the advertised input schema before conversion; reject wrong types and invalid bounds with `-32602`. |
| MR-020 | Public validator accepts directories as required files | P2 | `FINDINGS-luna-a.md` | `tools/validate_public.py:187-190` | Require regular in-root files and reject symlinks/directories for required public paths. |
| MR-021 | Public asset validation follows symlinks outside the root | P2 | `FINDINGS-luna-a.md` | `tools/validate_public.py:316-321` | Reject symlinks, enforce resolved containment, catch I/O failures, and share the main walk’s size policy. |
| MR-022 | File presence is overstated as test and CI evidence | P2 | `FINDINGS-sol.md`; test-discovery component in `FINDINGS-luna-a.md` | `tools/checkyourself.py:1411-1421`; `skills/checkyourself/SKILL.md:36-38,89-90` | Report presence as Detected/Unknown unless focused execution or parsing supplies a receipt; keep discovery and proof distinct. |
| MR-023 | Coverage completeness accepts duplicate and mismatched canonical rows | P2 | `FINDINGS-sol.md` | `tools/checkyourself.py:1167-1192` | Require exactly 20 unique canonical ID/surface/category tuples and schema validity before completeness checks. |
| MR-024 | README dashboard image is broken | P2 | `FINDINGS-luna-b.md`, `FINDINGS-sol.md` | `README.md:200`; existing asset `10_DASHBOARD/output/checkyourself-dogfood-dashboard-live-20260612.png` | Point README to the intended existing asset or add the deliberate canonical filename; run public validation. |
| MR-025 | README describes shipped MCP support as future work | P2 | `FINDINGS-luna-b.md`, `FINDINGS-sol.md` | `README.md:190`; `docs/mcp.md:3`; `tools/checkyourself.py:2116-2323,2581-2582` | Describe MCP as shipped while preserving the local/no-hosted-API boundary. |
| MR-026 | Adapter guidance omits current native CLI/MCP clients | P2 | `FINDINGS-sol.md` | `06_ADAPTERS/README.md:3-9`; `tools/checkyourself.py:1679-1735,2116-2323` | Add one canonical native-agent/MCP adapter and reduce provider adapters to deltas, including discovery and write boundaries. |
| MR-027 | Promised contract test matrix is incomplete | P2 | `FINDINGS-sol.md`, `FINDINGS-dsv4.md` | `docs/agent-access-cli-plan.md:314-323`; `tests/test_checkyourself_cli.py:522-587,665-678` | Add table-driven negative/positive tests for all verbs, caps, transitions, schemas, invalid evidence, mutation defaults, and normalized goldens. |
| MR-028 | README and FAQ deny the shipped optional CLI | P2 | `FINDINGS-luna-b.md` | `README.md:68,185,188,253`; `START_HERE.md:27-35` | Say “no required command line” and “optional CLI,” aligned with START_HERE and CLI docs. |
| MR-029 | `llms.txt` points detector-rule readers to the wrong authority | P2 | `FINDINGS-luna-b.md` | `llms.txt:14`; `rules.md:1-23`; `docs/cli.md:84-110` | Describe `rules.md` accurately and link detector rules to the canonical table. |
| MR-030 | Implemented agent-access plan still reads as proposed and permits removed state | P2 | `FINDINGS-luna-b.md` | `docs/agent-access-cli-plan.md:3,123-124,171-173,280,298,329-338`; `CHANGELOG.md:61-63` | Convert the plan into a current decision record and remove `blocked` in favor of canonical `open` plus blocker context. |
| MR-031 | NotApplicable scoring math conflicts across authoritative-looking docs | P2 | `FINDINGS-luna-b.md`, `FINDINGS-sol.md` | `02_RUN_DIAGNOSTIC/scoring-method.md:22`; `docs/agent-access-cli-plan.md:218-221`; `tools/checkyourself.py:1450-1477` | Declare scoring-method/`describe` canonical, correct or archive the plan, and lock behavior with a test. |
| MR-032 | Complete-backlog template omits promised impact and touched-files fields | P2 | `FINDINGS-luna-b.md` | `skills/checkyourself/SKILL.md:61-62`; `05_OUTPUT_TEMPLATES/production-reality-report.md:111-132` | Add the two fields per backlog row or require a per-item fix card; validate a generated report. |
| MR-033 | Inline-dashboard trigger is missing from template guidance | P2 | `FINDINGS-luna-b.md`; trigger ambiguity noted in `FINDINGS-floor-champion.md` | `skills/checkyourself/SKILL.md:95-99`; `05_OUTPUT_TEMPLATES/README.md:25`; `10_DASHBOARD/README.md:43-47` | Document both `dashboard yes` and `dashboard inline` wherever generation is gated. |
| MR-034 | Security support policy is stale after tagged releases | P2 | `FINDINGS-luna-b.md` | `SECURITY.md:7-9`; `CHANGELOG.md:3` | State which released versions and branch are supported; add a release checklist assertion. |
| MR-035 | Top-level CLI help hides shipped subcommands | P2 | `FINDINGS-luna-b.md` | `tools/checkyourself.py:2509-2583,2596-2610`; `docs/cli.md:30-47` | Route top-level `--help` to subcommand help while preserving explicit legacy scan behavior; test both. |
| MR-036 | Human coverage vocabulary drifts from the machine enum | P2 | `FINDINGS-luna-b.md` | `02_RUN_DIAGNOSTIC/coverage-matrix.md:35-39`; `05_OUTPUT_TEMPLATES/production-reality-report.md:63`; `02_RUN_DIAGNOSTIC/CONTEXT.md:26` | Use “Not applicable” in prose and reserve `NotApplicable` for JSON, with one explicit mapping. |
| MR-037 | Markdown validator rejects valid links with titles | P3 | `FINDINGS-luna-a.md` | `tools/validate_public.py:288-300` | Parse destinations and optional titles correctly, including escaped and angle-bracket forms. |
| MR-038 | **CONTENDED:** manual fallback cannot guarantee deterministic IDs | P3 | `FINDINGS-floor-crack.md`, `FINDINGS-floor-champion.md`, `FINDINGS-dsv4.md` | `skills/checkyourself/SKILL.md:27-38` | Define a canonical manual rule-ID registry and evidence rubric, or explicitly label manual output non-deterministic. The engine exists in this repository, so this applies only to copied/partial installations. |
| MR-039 | **CONTENDED:** cap precedence and evidence sufficiency are unclear to skill-only readers | P3 | `FINDINGS-floor-crack.md`, `FINDINGS-floor-champion.md` | `skills/checkyourself/SKILL.md:49-53,89-90`; implementation behavior at `tools/checkyourself.py:1450-1477` | State the base-score-to-minimum-cap formula and concrete evidence bars in the skill or directly link one canonical executable contract. No conflicting runtime result was reproduced. |

## Fix waves

Each wave assumes a clean committed baseline and produces its own commit. No wave relies on another wave’s uncommitted state. Every wave contains at most ten findings.

### W1 — Fail closed at the score trust boundary

- **Scope:** `tools/checkyourself.py`, `tests/test_checkyourself_cli.py` (and the existing MCP test module if separate).
- **Rows:** MR-001.
- **Acceptance:** `python3 -m pytest tests/ -q` exits 0, and focused fixtures for invalid, null, duplicate, unknown-ID, and mismatched-category coverage all make CLI and MCP scoring reject the artifact without returning a score/confidence.
- **Rollback:** Revert the single wave commit; no artifact/schema migration is included.

### W2 — Make schemas prove their advertised contracts

- **Scope:** `tools/checkyourself.py`, `schemas/dashboard-data.schema.json`, `schemas/checkyourself-report.schema.json`, `tests/test_checkyourself_cli.py`.
- **Rows:** MR-003, MR-004.
- **Acceptance:** `python3 -m pytest tests/ -q` exits 0; `{}` and `{"garbage":true}` fail dashboard validation; omission of each required report section fails; golden dashboard/report fixtures pass in CLI and MCP.
- **Rollback:** Revert the wave commit and its schema version bump together; consumers remain on the prior schema.

### W3 — Restore scanner completeness and safe writes

- **Scope:** `tools/checkyourself.py`, `tests/test_checkyourself_cli.py`.
- **Rows:** MR-002, MR-007, MR-008, MR-009, MR-010.
- **Acceptance:** `python3 -m pytest tests/ -q` exits 0; audit commands leave a fixture tree byte-for-byte unchanged by default; skipped/truncated inputs mark scans incomplete; Dockerfile secrets are detected; `latest.py` is not a test; symlink-parent output is rejected.
- **Rollback:** Revert the wave commit; explicit output artifacts created during testing are fixture-local and removable.

### W4 — Make backlog and diff semantics truthful

- **Scope:** `tools/checkyourself.py`, `docs/agent-access-cli-plan.md`, `tests/test_checkyourself_cli.py`.
- **Rows:** MR-005, MR-006, MR-017.
- **Acceptance:** `python3 -m pytest tests/ -q` exits 0; equal-count P1 replacement makes `diff --ci` fail; open-to-fixed appears in `resolved`; batch output either has machine-checkable dependency/safety rationale or is named `highest_severity_batch`.
- **Rollback:** Revert the wave commit; preserve old output field aliases for one version if compatibility is required.

### W5 — Harden malformed-input and configuration handling

- **Scope:** `tools/checkyourself.py`, `tests/test_checkyourself_cli.py` (and the existing MCP test module if separate).
- **Rows:** MR-013, MR-014, MR-015, MR-016, MR-018, MR-019, MR-023, MR-035.
- **Acceptance:** `python3 -m pytest tests/ -q` exits 0; malformed shapes/configs produce stable structured errors without tracebacks; gitignore fixtures honor patterns/comments; env variants agree; MCP rejects wrong types with `-32602`; coverage rejects structural drift; top-level help lists every shipped subcommand.
- **Rollback:** Revert the wave commit; no persisted user data changes.

### W6 — Align discovered evidence with proven evidence

- **Scope:** `tools/checkyourself.py`, `tests/test_checkyourself_cli.py`, `docs/agent-access-cli-plan.md`.
- **Rows:** MR-022, MR-027.
- **Acceptance:** `python3 -m pytest tests/ -q` exits 0; empty tests and invalid CI files cannot produce Pass; all plan-promised caps, schema failures, transitions, read-only defaults, deterministic goldens, and CLI/MCP pipelines have explicit tests.
- **Rollback:** Revert the wave commit; scanner output contract returns to the preceding version with no migration.

### W7 — Harden the public validator

- **Scope:** `tools/validate_public.py`, `tests/test_validate_public.py`.
- **Rows:** MR-020, MR-021, MR-037.
- **Acceptance:** `python3 -m pytest tests/test_validate_public.py -q` exits 0; directory stand-ins and out-of-root asset symlinks fail safely, while valid Markdown links with titles pass.
- **Rollback:** Revert the wave commit; public assets are not modified.

### W8 — Repair public truth and current proof

- **Scope:** `README.md`, `checkyourself.manifest.json`, `LICENSE`, `NOTICE.md`, `02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-recheck-report.md`, `10_DASHBOARD/output/TASTECHECK-PASS.md`, `10_DASHBOARD/output/checkyourself-dogfood-dashboard-live-20260612.png` (or its deliberate replacement).
- **Rows:** MR-011, MR-012, MR-024, MR-025, MR-028.
- **Acceptance:** after the owner supplies the license decision, `python3 tools/validate_public.py && python3 -m pytest tests/ -q` exits 0; all license/CLI/MCP/image claims agree; regenerated receipts include current command results and dates.
- **Rollback:** Revert the wave commit as a unit; keep prior receipts only under an explicitly historical label.

### W9 — Reconcile canonical documentation and templates

- **Scope:** `llms.txt`, `rules.md`, `docs/cli.md`, `docs/agent-access-cli-plan.md`, `02_RUN_DIAGNOSTIC/scoring-method.md`, `02_RUN_DIAGNOSTIC/coverage-matrix.md`, `02_RUN_DIAGNOSTIC/CONTEXT.md`, `05_OUTPUT_TEMPLATES/README.md`, `05_OUTPUT_TEMPLATES/production-reality-report.md`, `10_DASHBOARD/README.md`, `skills/checkyourself/SKILL.md`.
- **Rows:** MR-029, MR-030, MR-031, MR-032, MR-033, MR-036, MR-038, MR-039.
- **Acceptance:** `python3 tools/validate_public.py && python3 -m pytest tests/ -q` exits 0; a repository-wide contract check finds one detector-rule authority, one scoring formula, canonical lifecycle values, complete backlog fields, both dashboard triggers, and an explicit manual-fallback/evidence contract.
- **Rollback:** Revert the documentation wave commit; no runtime behavior changes.

### W10 — Modernize adapters and support policy

- **Scope:** `06_ADAPTERS/README.md`, the adapter files beneath `06_ADAPTERS/`, `docs/mcp.md`, `docs/cli.md`, `SECURITY.md`, release-validation tests/checklist.
- **Rows:** MR-026, MR-034.
- **Acceptance:** `python3 tools/validate_public.py && python3 -m pytest tests/ -q` exits 0; adapter smoke review covers native CLI/MCP discovery and write boundaries; SECURITY names supported releases/main unambiguously.
- **Rollback:** Revert the wave commit; existing runtime interfaces remain unchanged.

