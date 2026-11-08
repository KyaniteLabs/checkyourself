# Architecture

CheckYourself combines a staged Markdown diagnostic workspace with a local,
stdlib-only Python evidence engine. It is not a hosted service or a production
safety certification. This map describes implemented main-branch behavior;
unmerged plugin proposals are not installed capabilities.

## Components and accountable owners

- **Product** owns the experience and diagnostic guidance: `CONTEXT.md`,
  `00_START_HERE/` through `06_ADAPTERS/`, `10_DASHBOARD/`, `90_ADVANCED/`,
  `skills/`, and `reference/`. Stages gather context, diagnose, request approval,
  guide fixes, and teach; dashboards are opt-in.
- **Engineering** owns `tools/checkyourself.py` and `tools/checkyourself/`.
  `cli.py` dispatches commands; `scanning.py`, `scan.py`, and `detectors.py`
  inventory bounded local files and emit stable-ID findings. `coverage.py`,
  `scoring.py`, and `planning.py` check evidence, cap scores, and rank work.
  `challenge_config.py`, `challenge_run.py`, and `receipts.py` execute and
  revalidate project challenge evidence. `mcp.py` exposes the same functions
  over newline-delimited JSON-RPC stdio, not a separate scoring engine.
- **Engineering** owns machine contracts in `schemas/` and
  `checkyourself.manifest.json`, the Node-to-Python launcher
  `bin/checkyourself.mjs`, packaging in `package.json`/`Dockerfile`, and checks
  under `tests/`, `tools/validate_public.py`, and both forge workflow folders.
  Product owns the static `index.html` and explanatory `docs/`.
  `qa/architecture-paths.json` records these accountable boundaries; it does
  not by itself authorize adoption or validate empirical claims.

## One evidence flow

A user requests a diagnostic through the staged context or CLI. `scan` inventories
project files and returns findings plus limits; coverage adds reviewed evidence.
`challenge` runs committed `.checkyourself/challenges.json` argv commands and
stores execution captures/receipts. `score` validates evidence and re-executes
stored executed challenges before granting credit, applying category weights and
severity/evidence caps. `backlog`/`next` order unresolved work; a human approves
changes, then rechecks. Report, learning-plan and dashboard templates turn those
artifacts into reviewable outputs, not autonomous remediation.

## Trust, persistence, and dangerous changes

Project files, coverage declarations, challenge definitions, and MCP arguments
are untrusted inputs. MCP resolves scan paths beneath `CHECKYOURSELF_SCAN_ROOT`
(default process working directory). This path boundary is **not a sandbox**:
challenge execution and score-time re-execution run project commands with host
process privileges; commands can mutate files or access networks. Read-only MCP
annotations must not be mistaken for subprocess isolation.

CLI output/history writes live in `cli.py`/`output.py`; challenge artifacts and
project-local integrity keys live under `.checkyourself/`. Local HMAC/digest
bindings detect certain edits, not independent custody or operator identity.
Markdown stage `output/` folders hold user-requested reports; no database or
hosted account is required. Do not commit private findings or secret captures.

Changes to scoring/caps, receipt validation, subprocess timeouts, symlink/path
resolution, suppression rules, schema validation, package inclusion, or CI are
high-risk. Watch for rejected/changed receipts, incomplete scans, unknown
coverage, schema errors, subprocess failures/timeouts, and CLI nonzero exits;
a clean scanner is not proof of production safety.

## Verification and limits

Run `python3 -m unittest discover -s tests`,
`python3 tools/validate_public.py`, and `python3 tools/lint_sizes.py`.
`tests/test_architecture_contract.py` checks identity, path matches, and read-first
instructions. GitHub `.github/workflows/validate.yml` additionally exercises
CLI/MCP contracts, lint and secret scanning; `.forgejo/workflows/ci.yml` has its
own execution path. See `qa/foundation-gaps.md` for unproved packaging/browser,
mirror, and hosted-CI boundaries. Neither workflow presence nor local passing
tests proves mirror adoption or deployment health.
