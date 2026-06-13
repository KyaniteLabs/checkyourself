# CheckYourself Dogfood Recheck Report

Generated: 2026-06-12 (v1.7.0). Previous recheck: 2026-05-29 (v1.6.1).

## Score Change

After the v1.6.1 UltraQA pass: 100 / 100 (coverage-backed, high confidence).
After the v1.7.0 hardening pass: 100 / 100 (coverage-backed, high confidence),
re-earned under stricter rules — the v1.7.0 scoring engine closes the gaming
vectors that made a thin 100 possible, so this 100 means more than the last one:

- omitted coverage surfaces now count as Unknown instead of full credit;
- Pass entries without evidence and NotApplicable entries without a reason
  downgrade to Unknown;
- the 84/90 evidence caps apply in every score mode, including estimates;
- high confidence requires all 20 surfaces present with real evidence.

## What the v1.7.0 audit found and fixed

The audit that produced v1.7.0 found real defects in CheckYourself itself,
which is the point of dogfooding:

| Severity | Finding | Resolution |
|---|---|---|
| P0-class | A coverage artifact with omitted or thin "Pass" surfaces could score a perfect 100 with high confidence. | Scoring engine rewritten; regression-tested. |
| P1-class | The secret scanner stopped after the first high+low confidence hits in a file, missing later credentials. | Early break removed; multi-credential regression test added. |
| P1-class | Symlinked files inside a scanned project were followed and read out-of-tree. | Symlinks skipped and disclosed in `scan_limits`; containment enforced. |
| P1-class | MCP `scan` accepted any absolute host path, and misspelled tool arguments were silently ignored (scanning the wrong directory while reporting success). | Scan-root confinement plus strict argument validation. |
| P2-class | The 6,000-file scan cap truncated silently. | Truncation disclosed in output, configurable via `--max-files`. |
| P2-class | The composite GitHub Action interpolated inputs into shell — a script-injection sink for consumers. | Inputs now pass through env vars. |

## Current Status

| Severity | Open | Notes |
|---|---:|---|
| P0 | 0 | Test fixtures build credential shapes by string concatenation, so no secret finding fires and no suppression is needed. |
| P1 | 0 | — |
| P2 | 0 | One reviewed suppression: CY-CODE-001 for the detector regex definitions themselves, path-scoped in `.checkyourself.yml`. |
| P3 | 0 | — |

## 100/100 Receipts (v1.7.0)

- `python3 tools/checkyourself.py scan . --deep --ci` exits 0: zero unresolved
  findings, one reviewed path-scoped suppression visible in JSON.
- `python3 tools/checkyourself.py coverage --check 02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-coverage.json`
  reports complete with zero warnings (Pass evidence carries file/test receipts).
- `python3 tools/checkyourself.py score --findings <scan.json> --coverage 02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-coverage.json`
  returns 100, high confidence, no caps — under the stricter v1.7.0 anti-gaming rules.
- `python3 -m pytest tests/` passes 60 tests, including regression tests for
  every defect listed above.
- `ruff check tools/ tests/` and `python3 tools/validate_public.py` pass.
- MCP smoke test passes `initialize`, `tools/list`, `tools/call`, rejects
  unknown tools/arguments with JSON-RPC errors, and confines scans to the
  configured scan root.

## Remaining Work

No launch-blocking CheckYourself findings remain. Tracked next steps are
product growth, not score-blocking remediation: a labeled benchmark corpus with
precision/recall reporting, deeper platform-specific findings for detected
edge/serverless targets, and broader cross-agent eval samples.
