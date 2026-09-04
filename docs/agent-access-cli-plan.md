# Build Plan — Agent-Accessible CheckYourself CLI

Status: **implemented in v1.6.0.** This document is now the decision record for
turning `tools/checkyourself.py` from a one-shot scanner into the machine interface that lets an
AI agent **discover, run, score, and self-verify** CheckYourself with no human in the loop.

Current decision: **CLI is the canonical engine, MCP is a thin local wrapper, no hosted API for
now.** The CLI is local, offline, scriptable, CI-friendly, and easiest for AI agents to call
through an existing shell tool. The MCP server wraps the same CLI functions for native agent tools.
A hosted HTTP API is intentionally out of scope unless CheckYourself becomes a SaaS/team service;
it would add auth, hosting, privacy, support, and attack-surface work that the current open-source
folder/CLI product does not need.

It is grounded in the existing system: `02_RUN_DIAGNOSTIC/scoring-method.md`,
`02_RUN_DIAGNOSTIC/coverage-matrix.md`, `AGENTS.md`, and `schemas/`.

---

## 1. Guiding principle: split judgment from determinism

The single design idea behind everything below:

- **The agent supplies judgment** — what it found (findings), which surfaces it inspected
  (coverage), what evidence it reviewed.
- **The CLI owns determinism** — it computes the score from `scoring-method.md` (weights +
  caps), ranks the backlog, selects the next safe batch, and validates output against
  `schemas/`.

Today an LLM eyeballs the score. That is neither reproducible nor verifiable. When the CLI
owns the math and the schemas, **any agent, any model, gets the same score from the same
evidence and can prove its own output conforms.** That is what makes CheckYourself truly
agent-usable instead of merely agent-runnable.

### Goals

- An agent can introspect the whole tool from one command.
- Scoring and backlog ranking are reproducible and offline.
- Every output is JSON that conforms to a published schema.
- Zero third-party dependencies; runs anywhere Python 3.8+ runs; never prints secret values.

### Non-goals

- Replacing the AI-driven diagnostic. The CLI is the deterministic scaffold; the agent still
  sweeps the surface, explains risks, and writes the learning plan.
- Network calls, telemetry, or any data leaving the machine.
- A heavyweight framework or packaging (no pip publish required to use it).
- A hosted HTTP API. The local CLI already gives humans, CI, and agents a stable interface; API work
  belongs to a later service product, not this repository's launch surface.

---

## 2. The four pillars → requirements

| Pillar | Requirement | Delivered by |
|---|---|---|
| Agent-findable | One call returns the full capability surface | `describe`, `AGENTS.md` pointer, manifest entrypoint |
| Agent-readable | Structured, schema-backed output everywhere | `--format json`, `schema`, stable IDs/enums |
| Agent-usable | The whole workflow exposed as callable verbs | `scan`, `coverage`, `score`, `backlog`, `next`, `validate` |
| Agent-accessible | Zero-dep, offline, deterministic, native tool access | stdlib, stable exit codes, local `mcp` server |

---

## 3. Command surface

The CLI moves to a subcommand model. **Backward compatibility:** the current bare invocation
`checkyourself <path>` continues to mean `scan <path>` so nothing that exists today breaks.

Global conventions:
- `--format {json,text}` where useful (default `text` for humans, `json` for agent-first emitters).
- `--out PATH` / `--json [PATH]` for file output; generated files keep the gitignored
  `CHECKYOURSELF_*.generated.*` names.
- Stable, documented exit codes (see §6).
- No command ever prints a secret value.

### 3.1 `describe` — the discovery entrypoint (findable)

- **Purpose:** emit a single JSON capabilities manifest so an agent learns the entire tool in
  one call.
- **Output:** `{ tool, version, commands:[{name, summary, inputs, outputs, schema, exit_codes}],
  coverage_surfaces:[...20...], scoring:{weights, caps, confidence_labels}, schemas:[...] }`.
- **Determinism:** pure; derived from constants and the bundled schema/method files.
- **Example:** `python3 tools/checkyourself.py describe --format json`

### 3.2 `scan` — deterministic discovery (built, to extend)

- **Purpose:** detect stack, dependencies, scripts, env files, tests, CI, risk-surface path
  hints; raise deterministic findings (credential shapes, lower-confidence secret-like
  assignments, committed `.env`, missing `.env.example`, no tests, no CI) ranked P0-P3.
- **Extend with:** `--format json` returning a `checkyourself-scan/1` object that already
  carries `findings[]` and `counts` so it can pipe straight into `score` and `backlog`.
- **Output:** context Markdown + scan JSON with suppression status. `diagnostic` is an alias
  for `scan`, and `scan --deep` adds conservative CI/supply-chain validation checks.

### 3.3 `coverage` — the 20-surface matrix (usable)

- **Purpose:** operationalize `coverage-matrix.md`.
- **Modes:**
  - `coverage --emit` → writes `CHECKYOURSELF_COVERAGE.generated.json` by default in text
    mode; `--format json` prints the skeleton to stdout for pipelines. The skeleton has all
    20 surfaces with `status` unset, ready for the agent to fill
    (`Pass|Finding|Unknown|NotApplicable`) plus `evidence_reviewed[]` / `missing_evidence[]`.
  - `coverage --check FILE` → validate a filled-in coverage doc against the **completeness rule**
    (every surface represented; criticals not silently skipped). Non-zero exit if incomplete.
- **Output:** conforms to a new `schemas/coverage.schema.json` (see §4).

### 3.4 `score` — reproducible Production Reality Score (usable, the keystone)

- **Purpose:** deterministically compute the 0–100 score from findings + coverage, applying the
  weights and caps in `scoring-method.md`.
- **Input:** `score --findings findings.json [--coverage coverage.json]`.
- **Algorithm:** coverage-backed scores apply the full evidence caps. Without coverage, scan
  JSON produces a low-confidence `scan-derived-estimate` and lists `manual_evidence_needed`.
  Detected test or CI paths are discovery signals only: they remain `Unknown` until a focused
  test-execution or CI parse/success receipt is supplied.
- **Output:** `{ score, confidence, per_category:[{category, weight, raw, penalties[], awarded}],
  caps_applied:[...], score_mode, manual_evidence_needed, counts }` conforming to
  `schemas/score-result.schema.json`.
- **Why it matters:** the score stops being a vibe. Same evidence → same number, every time.

### 3.5 `backlog` / `next` — ranking and the highest-severity batch (usable)

- **`backlog --findings F`:** rank every Finding and high-impact Unknown by
  severity → category → finding ID; output the **complete ranked backlog** plus the
  **`highest_severity_batch`** (at most three unresolved findings at the highest severity).
  The CLI does not analyze reversibility, dependencies, coupling, or blast radius, so this field is
  not a safety judgment. `first_approval_batch` remains as a compatibility alias.
- **`next --findings F`:** given current statuses (fixed / accepted-risk / deferred /
  not-applicable), emit the next `highest_severity_batch` using the same deterministic rule.
  The result also retains `next_approval_batch` as a compatibility alias.
- **Output:** the complete backlog and batch basis are machine-readable; consumers should use
  `batch_basis.name` to distinguish the highest-severity slice from a future safety-ranked batch.

### 3.5.1 `diff` — identity-aware regression gate

- `diff` reports status-only open-to-resolved transitions in `resolved` and details every
  status/severity transition separately.
- `diff --ci` fails for a newly open P0/P1 finding, a reopened P0/P1 finding, a severity escalation
  into open P0/P1, or an increased aggregate open P0/P1 count. Identity events are retained in
  `regressions`; count-only changes are reported as `count_regression`.

### 3.6 `validate` — schema self-check (readable / accessible)

- **Purpose:** let an agent prove its own output is well-formed, and let CI gate on it.
- **Input:** `validate --kind {report,dashboard,learning-plan,scan,coverage,score} FILE`.
- **Behavior:** validate against the matching schema in `schemas/`; print errors; non-zero exit
  on invalid.
- **Note:** implement a small stdlib JSON-Schema subset checker (required/type/enum/min/max/items)
  to stay dependency-free; document the supported subset.

### 3.7 `schema` — emit a contract (readable)

- **Purpose:** `schema <name>` prints a named JSON schema to stdout so an agent can fetch the
  exact contract it must satisfy.
- **Determinism:** pure file passthrough from `schemas/`.

### 3.8 `init` — scaffold working files (accessible, optional)

- **Purpose:** drop the minimal CheckYourself working artifacts (output dirs, a stub coverage
  file) into a target project so an agent has somewhere to write handoffs.
- **Safety:** never overwrite without `--force`; read-only by default.

---

## 4. Data contracts (schemas)

Reuse the existing schemas where they already fit; add the missing machine contracts.

**Reuse:** `schemas/checkyourself-report.schema.json`, `schemas/dashboard-data.schema.json`,
`schemas/learning-plan.schema.json`. (A separate `checkyourself-dashboard.schema.json`
was reused initially and retired in v1.7.0; `dashboard-data.schema.json` covers both modes.)

**Add:**
- `schemas/scan.schema.json` — the `checkyourself-scan/1` object `scan` emits.
- `schemas/coverage.schema.json` — the 20-surface matrix with status enum + evidence arrays.
- `schemas/score-result.schema.json` — the `score` breakdown (per-category, caps, confidence).
- `schemas/backlog.schema.json` — the ranked backlog and first approval batch.
- `schemas/next-batch.schema.json` — the next unresolved approval batch.
- `schemas/capabilities.schema.json` — the `describe` manifest shape.

Every new schema must be added to the public validator's JSON checks and link-checked.

---

## 5. Deterministic scoring algorithm (proposed)

This operationalizes `scoring-method.md`. Tunable, but must stay faithful to that file.

**Categories and weights** (sum = 100), taken verbatim from `scoring-method.md`:

| # | Category | Weight |
|---:|---|---:|
| C1 | Data, privacy, tenant/user isolation | 18 |
| C2 | Auth, permissions, session safety | 14 |
| C3 | Secrets, environment, runtime config | 10 |
| C4 | API, validation, uploads, business logic | 10 |
| C5 | Testing and quality gates | 10 |
| C6 | Deployment, release, rollback, CI/CD | 8 |
| C7 | Observability, logs, errors, incident response | 8 |
| C8 | Performance, scaling, caching, rate limits | 8 |
| C9 | Frontend UX, accessibility, client safety | 8 |
| C10 | AI/RAG/agent governance (if applicable) | 6 |

**Surface → category map** (the 20 coverage surfaces feed the 10 scoring categories):

| Surfaces (from coverage-matrix.md) | Category |
|---|---|
| 6 Data storage, 7 User/tenant isolation, 10 Privacy, 18 Availability/recovery | C1 |
| 5 Auth & permissions | C2 |
| 8 Secrets & env | C3 |
| 4 API/backend, 9 Security/threat model | C4 |
| 11 Tests & quality gates | C5 |
| 12 CI/CD & supply chain, 13 Hosting/deploy/rollback, 14 Cloud/IaC | C6 |
| 17 Observability & incident response | C7 |
| 15 Performance/caching/rate limits, 16 Scaling/resilience | C8 |
| 3 Frontend UX & client safety | C9 |
| 19 AI/RAG/agent governance | C10 |
| 1 Product purpose, 2 Stack/architecture | context only (not scored) |
| 20 Learning needs | feeds learning plan (not scored) |

**Computation:**
1. Start from evidence, not assumed readiness. A category earns points only from applicable
   coverage surfaces with supporting evidence.
2. For each applicable scored category, derive an evidence state from the mapped coverage
   surfaces: `PassWithEvidence`, `Finding`, `Unknown`, or `NotApplicable`.
3. `PassWithEvidence` can earn the category's full weight. `Finding` starts from the evidenced
   baseline and subtracts a severity penalty mapped to that category: `P0 = 100%`, `P1 = 60%`,
   `P2 = 25%`, `P3 = 10%`; clamp at 0.
4. `Unknown` earns reduced or zero credit depending on criticality, records `missing_evidence`,
   and prevents high-confidence scoring. Critical unknowns in C1/C2/C3 should usually earn 0 until
   evidence is supplied.
5. `NotApplicable` categories are excluded from the denominator only when the report gives a
   concrete reason. Normalize across applicable categories without inflating scores for missing
   evidence.
6. Raw total = normalized sum of awarded category points (0–100).
7. **Apply caps** in order, taking the minimum:
   - any unresolved P0 → cap 49;
   - any unresolved P1 → cap 74;
   - missing evidence in a critical category (C1/C2/C3) → cap 84;
   - score > 90 requires evidence or justified not-applicable status for tests, secrets,
     deploy/rollback, observability, auth, and data boundaries; if any applicable evidence is
     absent, cap at 90.
8. **Confidence label** derived deterministically:
   - `high` — coverage complete and no `missing_evidence` in C1/C2/C3/C5;
   - `medium` — coverage complete but some non-critical evidence gaps;
   - `low` — coverage incomplete or critical evidence gaps.

Output records, per category, exactly what `scoring-method.md` asks for: evidence found, what was
missing, points awarded, and what would raise the score.

---

## 6. Exit codes (stable contract)

| Code | Meaning |
|---:|---|
| 0 | Success; no gating condition |
| 1 | Gating finding present (`--ci`: a P0; `validate`: invalid; `coverage --check`: incomplete) |
| 2 | Usage / input error (bad path, unparseable JSON, unknown `--kind`) |

---

## 7. CLI architecture

- Keep it **standard library only**. Prefer a single `tools/checkyourself.py` with an internal
  command registry; if it grows past ~800 lines, split into a `tools/checkyourself/` package with
  one module per command and a thin `__main__.py`. Either way the public path stays
  `tools/checkyourself.py` (file or package entry).
- `argparse` subparsers; each command is a small pure-ish function returning a dict, with a thin
  formatter for `text` vs `json` vs `md`.
- Scoring weights, caps, and the surface→category map live in one constants block so they are easy
  to keep in lockstep with `scoring-method.md` (a test asserts the weights sum to 100 and match
  that file).

---

## 8. API vs MCP vs CLI decision

**CLI** is the canonical interface for this repository. It is a local command-line program that can
be run by a person, CI, or an AI agent through shell access. It is enough for launch because it
keeps the product offline, zero-dependency, private-by-default, and easy to verify.

**MCP** (Model Context Protocol) is an optional agent integration layer. It exposes the same
commands as native tools inside Claude, Cursor, Codex, or other agent clients, and it calls the
same internal functions as the CLI.

**API** means a hosted HTTP service. It is not needed for the current public repository. Build one
only if CheckYourself becomes a remote SaaS/team product that needs accounts, shared history,
hosted runs, billing, or web dashboards. Until then, an API would mostly add operational burden and
security/privacy risk.

Recommendation: **ship CLI as the engine, ship MCP as a local wrapper, do not build an API now.**

## 9. MCP server (`checkyourself mcp`) — Phase 3

Make the verbs callable as **native agent tools** in Claude / Cursor / Codex.

- **Transport:** JSON-RPC 2.0 over stdio, implemented with the standard library only. The current
  MCP stdio transport uses newline-delimited JSON-RPC messages on stdin/stdout. No third-party MCP
  SDK, preserving the zero-dependency promise.
- **Handshake:** implements `initialize`, `notifications/initialized`, `ping`, `tools/list`, and
  `tools/call`.
- **Tools exposed:** `scan`, `coverage_emit`, `coverage_check`, `score`, `backlog`, `next`,
  `validate`, `describe` — each a thin wrapper over the same internal functions the CLI uses, so
  there is one implementation and one contract.
- **Inputs/outputs:** JSON arguments mirroring the CLI flags; results are the same schema-backed
  objects, returned as MCP tool content.
- **Sequencing:** built after the subcommand contract, so the MCP layer is a pure wrapper, not a
  parallel implementation.
- **Docs:** a `docs/mcp.md` with a ready-to-paste server entry for Claude Code / Cursor.

The native stdlib server is shipped as `python3 tools/checkyourself.py mcp`.

---

## 10. Discoverability wiring

- Add to `AGENTS.md`: a short "Machine interface" note — *"To discover and drive CheckYourself
  programmatically, run `python3 tools/checkyourself.py describe --format json`."*
- Add a `capabilities` pointer in `checkyourself.manifest.json` entrypoints.
- README: extend the "Optional local CLI" section with the agent-facing verbs.
- `docs/cli.md`: full command reference (expand from current scan-only docs).

---

## 11. Testing & verification

- **Fixtures:** a set of tiny sample projects under a test temp dir (clean app; app with a planted
  fake secret; app with committed `.env`; app with no tests/CI; AI/RAG app).
- **Golden outputs:** snapshot the JSON from `scan`/`score`/`backlog` for each fixture and assert
  determinism (same input → identical output).
- **Scoring tests:** assert weights sum to 100; assert each cap triggers (P0→≤49, P1→≤74,
  critical-evidence-gap→≤84, >90 gate); assert redistribution conserves total.
- **Schema conformance:** every emitted object validates against its schema via `validate`.
- **CI:** extend `.github/workflows/validate.yml` to compile the CLI, run `describe`, run a
  fixture `scan`→`score`→`validate` pipeline, and run the scoring unit tests.
- **No-secret guarantee test:** assert secret *values* never appear in any output.

The contract matrix is implemented in `tests/test_checkyourself_cli.py`. It also covers negative
schema artifacts through CLI and MCP, status-only and severity diff transitions, read-only scan and
score defaults, timestamp-normalized `scan`/`score`/`backlog` goldens, all documented score caps,
and the CLI/MCP `scan`→`score`→`validate` pipeline. File presence alone cannot certify tests or CI;
the scan-derived path records the missing execution or validation receipt instead.

---

## 12. Versioning, docs, release

- Target **v1.6.0** (new agent interface is a feature release).
- Update `CHANGELOG.md`, `checkyourself.manifest.json` (version, modes:
  add `agent_cli` / `mcp_server`; entrypoints: add `capabilities`), `docs/cli.md`, `docs/mcp.md`,
  README, and the new schemas — then run `tools/validate_public.py`.

---

## 13. Phased rollout & acceptance criteria

All phases below are delivered in v1.6.0 unless a future enhancement is called out explicitly.

**Phase 1A — Agent contract foundation**
- Add subcommands while preserving `python3 tools/checkyourself.py <path>` as `scan <path>`.
- Add `describe --format json`, `schema <name>`, stable exit codes, `scan --format json`, and
  stdout JSON support.
- Add `schemas/scan.schema.json` and `schemas/capabilities.schema.json`.
- Fix current scan-shape gaps: normalize `title/detail` with the report schema fields, make
  `--json --no-write` capable of writing JSON to stdout, and keep secret values redacted.
- *Delivered:* an agent can discover the tool, run `scan`, fetch schemas, and validate generated
  scan output offline with passing CI.

**Phase 1B — Deterministic scoring core**
- Add `score`, `validate`, and `schemas/score-result.schema.json`.
- Implement the evidence-first scoring algorithm above.
- *Delivered:* an agent can score findings and coverage reproducibly; tests prove the P0 cap and
  validation contract.

**Phase 2 — Full workflow**
- `coverage` (emit/check), `backlog`, `next`, `init`; `coverage` schema.
- *Delivered:* an agent can run the diagnose → score → backlog → next-batch loop through the CLI,
  and `coverage --check` enforces the completeness rule.

**Phase 3 — Native tool access (MCP)**
- `checkyourself mcp` stdio server + `docs/mcp.md`.
- *Delivered:* compatible MCP clients can call CheckYourself tools natively with a local stdio
  config and no third-party dependency.

---

## 14. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Scoring drift from `scoring-method.md` | One constants block + a test asserting weights/caps match the doc |
| Schema drift between CLI output and `schemas/` | `validate` runs in CI against real fixture output |
| Scope creep / two implementations | MCP is a thin wrapper over the same functions; one contract |
| Premature API work | Defer hosted API until there is a service product with real account/team requirements |
| Cross-platform breakage | stdlib only; CI on Linux runner; avoid OS-specific calls |
| Determinism leaks (timestamps, ordering) | Sort all collections; isolate `generated_at` to a single field; golden-output tests |
| Plan misread as a clean bill of health | Outputs restate that deterministic checks are a floor, not full coverage |

---

## 15. Resolved questions

1. Penalty fractions shipped as `P0=100%`, `P1=60%`, `P2=25%`, `P3=10%` of the mapped category.
2. The implementation stays in one `tools/checkyourself.py` file for now; split only if future
   growth makes review harder.
3. `init` is included because it gives agents a safe generated-file target without guessing paths.
4. MCP ships as the native stdlib server.
5. `score` and `backlog` accept scan output, report-like JSON, or raw findings arrays through the
   same normalization path.
