# Local CLI: `tools/checkyourself.py`

CheckYourself is still a folder-first audit system, but the CLI is now the
deterministic engine an agent can drive.

It uses only the Python standard library, sends nothing over the network, and
never prints secret values. The AI still supplies judgment. The CLI supplies
repeatable receipts: discovery, schemas, coverage checks, scoring, backlog
ranking, validation, and the thin MCP wrapper.

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
risk-surface path hints, and obvious deterministic risks:

- high-confidence credential-shaped values;
- lower-confidence secret-like assignments without known credential shapes;
- real `.env` files that may be committed;
- missing `.env.example`;
- missing tests;
- missing CI;
- payments dependencies without tests.

Package scripts are redacted before they appear in JSON or Markdown output. If a
script contains a credential-shaped value, the value is replaced with
`[REDACTED]`.

Evidence includes file, line, matched pattern type, confidence, and redacted
context. Known credential shapes can still create P0 findings. Name-only or
assignment-only signals are lower severity so schema fields like
`feedbackToken` do not wreck the score just for having an unfortunate name.

Projects can suppress reviewed false positives with `.checkyourself.yml`:

```yaml
version: 1
suppress:
  - id: CY-001
    reason: "feedbackToken is a UUID reference, not a credential"
    files: ["src/dispatcher/tool-registry.ts"]
    reviewed_by: simon
    reviewed_at: "2026-05-29"
```

Suppressed findings remain in JSON with `status: "suppressed"` and a
`suppression` note, but they do not count toward severity totals or score caps.

`scan --deep` is still intentionally conservative. It validates a few detected
surfaces instead of pretending to be a full SAST platform: mutable GitHub Action
refs, missing dependency update automation, and missing sensitive-file
`.gitignore` patterns.

The scan is not a clean bill of health. It is cheap evidence for the full
CheckYourself diagnostic.

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

The result includes `per_category` penalties, caps applied, confidence, and the
finding IDs scored.

With `--coverage`, the result is `score_mode: "coverage-backed"` and the normal
coverage caps apply. Without `--coverage`, the CLI produces a
`scan-derived-estimate` when the findings file is scan JSON. It uses only the
evidence the scan actually observed, keeps confidence `low`, and returns
`manual_evidence_needed` so nobody mistakes the estimate for launch permission.

Every score appends a receipt to `.checkyourself-score-history.json` beside the
findings file by default. Use `--history PATH` to choose a file, `--note` to add
context, or `--no-history` for disposable runs.

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
- `report`;
- `dashboard`;
- `dashboard-data`;
- `dashboard-html`;
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
`coverage_check`, `score`, `backlog`, `next`, `validate`, and `schema`.

See [`mcp.md`](mcp.md).

## API Decision

There is no hosted API in this repo.

The CLI is the canonical engine. MCP is a local convenience wrapper over that
engine. A hosted API only makes sense if CheckYourself becomes a SaaS/team
product with accounts, hosted runs, shared history, billing, or browser-only
usage.
