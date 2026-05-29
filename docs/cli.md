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
| `coverage --emit` | Emits the 20-surface coverage skeleton for an agent to fill. |
| `coverage --check FILE` | Checks a filled coverage artifact for completeness. |
| `score --findings FILE [--coverage FILE]` | Computes the deterministic Production Reality Score. |
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
python3 tools/checkyourself.py coverage --emit --format json > CHECKYOURSELF_COVERAGE.generated.json
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

## Scan

```bash
python3 tools/checkyourself.py scan /path/to/project
python3 tools/checkyourself.py scan . --json
python3 tools/checkyourself.py scan . --json -
python3 tools/checkyourself.py scan . --format json --no-write
python3 tools/checkyourself.py scan . --ci
```

`scan` detects stack signals, dependencies, scripts, env files, tests, CI,
risk-surface path hints, and obvious deterministic risks:

- possible hardcoded secrets or credential-shaped values;
- real `.env` files that may be committed;
- missing `.env.example`;
- missing tests;
- missing CI;
- payments dependencies without tests.

Package scripts are redacted before they appear in JSON or Markdown output. If a
script contains a credential-shaped value, the value is replaced with
`[REDACTED]`.

The scan is not a clean bill of health. It is cheap evidence for the full
CheckYourself diagnostic.

## Coverage

```bash
python3 tools/checkyourself.py coverage --emit --format json
python3 tools/checkyourself.py coverage --check CHECKYOURSELF_COVERAGE.generated.json
```

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
