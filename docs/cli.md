# Local CLI: `tools/checkyourself.py`

CheckYourself is still a folder-first audit system, but the CLI is now the
deterministic engine an agent can drive.

It uses only the Python standard library, sends nothing over the network, and
never prints secret values. The AI still supplies judgment. The CLI supplies
repeatable receipts: discovery, schemas, coverage checks, scoring, backlog
ranking, validation, and the thin MCP wrapper.

For native host setup, discovery, and write boundaries, see the canonical
[`native CLI/MCP adapter`](../06_ADAPTERS/native-cli-mcp.md).

## Fast Start

```bash
# Backward-compatible scan path
python3 tools/checkyourself.py /path/to/your/project

# Explicit scan subcommand
python3 tools/checkyourself.py scan /path/to/your/project

# Diagnostic alias for agent workflows that use that word
python3 tools/checkyourself.py diagnostic /path/to/your/project

# Machine-readable scan
python3 tools/checkyourself.py scan . --format json --no-write

# Discover every command and schema
python3 tools/checkyourself.py describe --format json
```

## Command Map

| Command | Purpose |
| --- | --- |
| `describe` | Emits the full machine-readable capability manifest. |
| `scan` | Detects stack signals and deterministic local findings. |
| `diagnostic` | Alias for `scan`, kept so docs and agents can use the natural workflow word. |
| `scan --deep` | Adds slower validation checks for detected surfaces, including mutable GitHub Actions and dependency-update coverage. |
| `coverage --emit` | Writes the 20-surface coverage skeleton for an agent to fill. Use `--format json` for stdout. |
| `coverage --check FILE` | Checks a filled coverage artifact for completeness. |
| `score --findings FILE [--coverage FILE]` | Computes the deterministic Production Reality Score or a low-confidence scan-derived estimate. |
| `backlog --findings FILE` | Ranks the complete remediation backlog. |
| `next --findings FILE` | Returns the next safest unresolved approval batch. |
| `diff --old FILE --new FILE` | Compares two findings artifacts and reports added, resolved, and regressed findings. |
| `validate --kind KIND FILE` | Validates JSON against bundled schema contracts. |
| `schema NAME` | Prints a bundled JSON schema. |
| `init [PROJECT]` | Creates starter generated context and coverage files. |
| `mcp` | Runs the stdio MCP server over the same functions. |

## Typical Agent Pipeline

```bash
python3 tools/checkyourself.py describe --format json > CHECKYOURSELF_CAPABILITIES.generated.json
python3 tools/checkyourself.py scan . --format json --no-write > CHECKYOURSELF_SCAN.generated.json
python3 tools/checkyourself.py coverage --emit
```

The agent then fills `CHECKYOURSELF_COVERAGE.generated.json` with evidence from
the full diagnostic and can run:

```bash
python3 tools/checkyourself.py coverage --check CHECKYOURSELF_COVERAGE.generated.json
python3 tools/checkyourself.py score --findings CHECKYOURSELF_SCAN.generated.json --coverage CHECKYOURSELF_COVERAGE.generated.json --format json
python3 tools/checkyourself.py backlog --findings CHECKYOURSELF_SCAN.generated.json --format json
python3 tools/checkyourself.py next --findings CHECKYOURSELF_SCAN.generated.json --format json
```

That makes the score and first batch reproducible. Same evidence, same score.
No vibes with a clipboard.

See the field notes behind this remediation in
[`docs/postmortems/checkyourself-field-postmortem-2026-05-29.md`](postmortems/checkyourself-field-postmortem-2026-05-29.md).

## Scan

```bash
python3 tools/checkyourself.py scan /path/to/project
python3 tools/checkyourself.py scan . --json
python3 tools/checkyourself.py scan . --json -
python3 tools/checkyourself.py scan . --format json --no-write
python3 tools/checkyourself.py scan . --ci
python3 tools/checkyourself.py scan . --deep --format json --no-write
```

`scan` detects stack signals, dependencies, scripts, env files, tests, CI,
risk-surface path hints, and obvious deterministic risks. Each finding has a
**stable, semantic rule ID** (for example `CY-SECRET-001`, `CY-CONFIG-001`)
that stays the same across runs and releases, so you can suppress, diff, and
cite findings reliably:

### Canonical detector-rule registry

The table below is the canonical detector-rule registry. `rules.md` defines the
human review and safety workflow; it is not a second detector-ID registry.
Manual reviewers reuse these IDs when the observed condition matches a shipped
detector and use the manual fallback contract in `skills/checkyourself/SKILL.md`
for conditions that the CLI does not detect.

| Rule ID | Severity | What it catches |
| --- | --- | --- |
| `CY-SECRET-001` | P0 | High-confidence credential-shaped values in source. |
| `CY-SECRET-002` | P2 | Secret-like assignments without a known credential shape. |
| `CY-SECRET-003` | P3 | Sensitive file patterns missing from `.gitignore` (deep). |
| `CY-ENV-001` | P0 | A real `.env` file that may be committed and is not gitignored. |
| `CY-ENV-002` | P2 | A local `.env` present; verify it was never committed. |
| `CY-ENV-003` | P1 | No `.env.example` for required configuration. |
| `CY-CONFIG-001` | P2 | Debug mode enabled in committed configuration. |
| `CY-CONFIG-002` | P1 | Default or weak credentials in committed configuration. |
| `CY-API-001` | P2 | CORS configured to allow any origin. |
| `CY-CODE-001` | P2 | Dangerous code patterns (eval, unsafe deserialization, disabled TLS, raw HTML injection). |
| `CY-WEB-001` | P3 | Production source maps enabled. |
| `CY-TEST-001` | P1 | No automated tests detected. |
| `CY-CI-001` | P2 | No CI pipeline detected. |
| `CY-PAY-001` | P1 | Payments dependency present but no tests. |
| `CY-AI-001` | P2 | LLM dependency present but no tests. |
| `CY-SUPPLY-001` | P2 | Mutable GitHub Action references (deep). |
| `CY-SUPPLY-002` | P2 | `package.json` with no committed lockfile. |
| `CY-SUPPLY-003` | P3 | No dependency update automation (deep). |
| `CY-SUPPLY-004` | P3 | CI uses `npm install` instead of `npm ci` (deep). |

Secrets are scanned in every file, including tests and docs, because real
credentials get committed in both. The lower-noise heuristic detectors (debug
flags, CORS, dangerous sinks, default credentials) skip test, fixture, doc, and
example paths to keep the false-positive rate low.

Package scripts and all evidence context are redacted before they appear in
JSON or Markdown output: credential-shaped values are replaced with
`[REDACTED]`. Evidence includes file, line, matched pattern type, confidence,
and redacted context. Name-only or assignment-only signals stay lower severity
so schema fields like `feedbackToken` do not wreck the score just for having an
unfortunate name. Env example variants such as `.env.dogfood.example`,
commented placeholders, and obvious placeholder values are treated as setup
documentation instead of real local secrets.

The scan never follows symlinks and never reads files outside the scanned tree;
skipped symlinks and unreadable files are reported in `scan_limits`. Large
projects are scanned up to `--max-files` (default 6000); when that cap is hit,
`scan_limits.truncated` is `true` and the count of skipped files is disclosed so
a partial scan is never mistaken for a clean one.

Projects can suppress reviewed false positives with `.checkyourself.yml`. Use
the stable rule ID and always scope it to the relevant path:

```yaml
version: 1
suppress:
  - id: CY-SECRET-002
    reason: "feedbackToken is a UUID reference, not a credential"
    files: ["src/dispatcher/tool-registry.ts"]
    reviewed_by: simon
    reviewed_at: "2026-06-12"
```

Suppressed findings remain in JSON with `status: "suppressed"` and a
`suppression` note, but they do not count toward severity totals or score caps.

`scan --deep` is still intentionally conservative. It validates a few detected
surfaces instead of pretending to be a full SAST platform: mutable GitHub Action
refs, missing dependency update automation, `npm install` in CI, and missing
sensitive-file `.gitignore` patterns.

The scan is not a clean bill of health. It is cheap evidence for the full
CheckYourself diagnostic.

## Diff

```bash
python3 tools/checkyourself.py diff --old baseline.json --new current.json
python3 tools/checkyourself.py diff --old baseline.json --new current.json --ci
python3 tools/checkyourself.py diff --old baseline.json --new current.json --format json
```

`diff` compares two findings artifacts (scan output, reports, or finding lists)
and reports which findings were **added**, **resolved**, and **unchanged**,
plus evidence-level changes on findings that persisted. Because rule IDs are
stable, the delta reflects real changes rather than ID-shuffle noise.

The result includes a `regression` flag that is `true` when the open P0 or P1
count increased against the baseline. With `--ci`, `diff` exits non-zero on a
regression, so CI can gate on *new* risk instead of only absolute P0 count —
the right control for a project that already has a known backlog.

## Coverage

```bash
python3 tools/checkyourself.py coverage --emit
python3 tools/checkyourself.py coverage --emit --format json > CHECKYOURSELF_COVERAGE.generated.json
python3 tools/checkyourself.py coverage --check CHECKYOURSELF_COVERAGE.generated.json
```

In text mode, `coverage --emit` writes
`CHECKYOURSELF_COVERAGE.generated.json` in the current directory. Use
`--out PATH` to choose a path, or `--format json` when another tool wants stdout.

Coverage has 20 surfaces. Each surface must be marked:

- `Pass`;
- `Finding`;
- `Unknown`;
- `NotApplicable`.

`Pass` needs evidence. `Unknown` needs missing evidence. `NotApplicable` needs a
reason.

## Scoring

```bash
python3 tools/checkyourself.py score --findings findings.json --coverage coverage.json --format json
python3 tools/checkyourself.py score --findings CHECKYOURSELF_SCAN.generated.json --format json
```

The score uses the weights and caps from
[`02_RUN_DIAGNOSTIC/scoring-method.md`](../02_RUN_DIAGNOSTIC/scoring-method.md):

- unresolved P0 caps the score at `49`;
- unresolved P1 caps the score at `74`;
- missing critical evidence caps at `84`;
- scores above `90` require evidence for tests, secrets, deploy/rollback,
  observability, auth, and data boundaries.

The evidence caps (`84` and `90`) apply in **every** score mode, including
estimates — an estimate without coverage evidence can never report a
launch-ready number. Absence of findings is treated as absence of evidence, not
proof of safety: a scan that finds no secrets leaves the secrets surface
`Unknown`, not `Pass`.

The result includes `per_category` penalties, caps applied, confidence, and the
finding IDs scored.

With `--coverage`, the result is `score_mode: "coverage-backed"`. A coverage
entry marked `Pass` without `evidence_reviewed`, or `NotApplicable` without a
reason, is downgraded to `Unknown`, and any surface omitted from the artifact
counts as `Unknown` — so omitting or hand-waving a surface can never score
better than honestly reporting it, and `confidence: "high"` requires all 20
required surfaces present with real evidence.

Without `--coverage`, the CLI produces a `scan-derived-estimate` when the
findings file is scan JSON, or a `finding-only-estimate` otherwise. Both keep
confidence `low` and return `manual_evidence_needed` so nobody mistakes the
estimate for launch permission.

Every score appends a receipt to `.checkyourself-score-history.json` beside the
findings file by default. History timestamps are UTC so receipts from laptops
and CI stay comparable, and a corrupt history file is preserved as
`.corrupt.bak` rather than overwritten. Use `--history PATH` to choose a file,
`--note` to add context, or `--no-history` for disposable runs. Scoring from
stdin (`--findings -`) does not write history unless `--history` is explicit.

## Validation

```bash
python3 tools/checkyourself.py schema scan
python3 tools/checkyourself.py validate --kind scan CHECKYOURSELF_SCAN.generated.json
python3 tools/checkyourself.py validate --kind score CHECKYOURSELF_SCORE.generated.json
```

Supported schema kinds:

- `capabilities`;
- `scan`;
- `coverage`;
- `score`;
- `backlog`;
- `next`;
- `diff`;
- `report`;
- `dashboard`;
- `dashboard-data`;
- `learning-plan`.

Validation uses a small standard-library JSON Schema subset: `required`, `type`,
`enum`, `minimum`, `maximum`, `properties`, and `items`.

## Exit Codes

| Code | Meaning |
| ---: | --- |
| `0` | Success; no gating condition. |
| `1` | Gating condition: `--ci` P0, invalid artifact, or incomplete coverage. |
| `2` | Usage/input error. |

## GitHub Action

This repo includes a composite action for projects that vendor or reference
CheckYourself in CI:

```yaml
name: Production Readiness Check
on: [pull_request]
jobs:
  checkyourself:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<pinned-sha>
      - uses: KyaniteLabs/checkyourself/.github/actions/checkyourself@main
        with:
          fail-on-p0: "true"
          deep: "true"
```

The action writes scan JSON, validates it, and fails the job when `fail-on-p0`
is enabled and unresolved P0 findings remain. Pin the action ref for production
use.

## MCP

The MCP wrapper is local stdio and thin by design:

```bash
python3 tools/checkyourself.py mcp
```

It exposes native tools for `describe`, `scan`, `coverage_emit`,
`coverage_check`, `score`, `backlog`, `next`, `diff`, `validate`, and `schema`.

MCP-initiated scans are confined to `CHECKYOURSELF_SCAN_ROOT` (defaulting to the
server process working directory). A `scan` request for a path outside that root
is rejected, and unknown or misspelled tool arguments are rejected rather than
silently ignored, so an agent cannot accidentally scan the wrong directory.

See [`mcp.md`](mcp.md).

## API Decision

There is no hosted API in this repo.

The CLI is the canonical engine. MCP is a local convenience wrapper over that
engine. A hosted API only makes sense if CheckYourself becomes a SaaS/team
product with accounts, hosted runs, shared history, billing, or browser-only
usage.
