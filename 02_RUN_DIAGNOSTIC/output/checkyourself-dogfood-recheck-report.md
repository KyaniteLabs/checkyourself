# CheckYourself Dogfood Recheck Report

Generated: 2026-09-04 (v1.7.0). This recheck supersedes the 2026-06-12
receipt and records the current repository validation state.

## Current score

The current scan and coverage artifact produce **100 / 100 (high confidence)**
under the v1.7.0 scoring rules:

- `python3 tools/checkyourself.py scan . --deep --ci --no-write` exits 0 after
  scanning 234 files. It reports zero open P0/P1/P2/P3 findings and one
  path-scoped suppression: `CY-CODE-001`.
- `python3 tools/checkyourself.py coverage --check 02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-coverage.json`
  exits 0 with `Coverage complete`.
- `python3 tools/checkyourself.py score --findings <(python3 tools/checkyourself.py scan . --deep --ci --format json --no-write) --coverage 02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-coverage.json --no-history`
  exits 0 with `Score: 100 (high confidence, raw 100)`.

## Historical v1.7.0 hardening

The audit that produced v1.7.0 found real defects in CheckYourself itself,
which is the point of dogfooding:

| Severity | Finding | Resolution |
|---|---|---|
| P0-class | A coverage artifact with omitted or thin "Pass" surfaces could score a perfect 100 with high confidence. | Scoring engine rewritten; regression-tested. |
| P1-class | The secret scanner stopped after the first high+low confidence hits in a file, missing later credentials. | Early break removed; multi-credential regression test added. |
| P1-class | Symlinked files inside a scanned project were followed and read out-of-tree. | Symlinks skipped and disclosed in `scan_limits`; containment enforced. |
| P1-class | MCP `scan` accepted any absolute host path, and misspelled tool arguments were silently ignored. | Scan-root confinement plus strict argument validation. |
| P2-class | The 6,000-file scan cap truncated silently. | Truncation disclosed in output, configurable via `--max-files`. |
| P2-class | The composite GitHub Action interpolated inputs into shell. | Inputs now pass through environment variables. |

## Current validation status

The W8 public-validation baseline remains outside the product surfaces being
repaired:

- `python3 tools/validate_public.py` exits 1 only for two known broken links
  inside `_retrofit-2026-09-04/`: the `target.md` example in
  `FINDINGS-luna-a.md` and the historical screenshot reference in
  `FINDINGS-luna-b.md`. Per the W8 brief, these are orchestrator-owned and
  ignored.
- `python3 -m pytest tests/ -q` records **89 passed, 53 subtests passed, 1
  failed**. The single failure is
  `ValidatePublicTests.test_real_repository_passes_validation`, caused by the
  same two known `_retrofit-2026-09-04/` links.

The README dashboard link now resolves to the committed
`10_DASHBOARD/output/checkyourself-dogfood-dashboard-live-20260612.png` asset.
