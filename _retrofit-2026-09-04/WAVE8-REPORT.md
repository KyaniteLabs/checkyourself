# WAVE 8 Report — Repair Public Truth and Current Proof

Status: DONE_WITH_CONCERNS

## Scope

Implemented only W8 rows MR-011, MR-012, MR-024, MR-025, and MR-028. The
owner ruling was applied as final: Apache-2.0 is the license of record, with
`LICENSE` as the legal artifact and `NOTICE.md` following Apache practice. No
license decision was made. No installs, network calls, or Git commands were
used.

## Per-row status

| Row | Status | Evidence |
|---|---|---|
| MR-011 | fixed | `README.md:7,268,283` now uses Apache-2.0 in the badge, FAQ, and footer. `checkyourself.manifest.json:5`, `LICENSE:1`, and `NOTICE.md:5` were independently verified as Apache-2.0 and required no edits. A consistency probe confirmed no MIT claim remains in `README.md`. |
| MR-012 | fixed with known baseline | `02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-recheck-report.md` and `10_DASHBOARD/output/TASTECHECK-PASS.md` were refreshed with 2026-09-04 evidence, current scan/coverage/score results, current test counts, and explicit labeling of the two orchestrator-owned `_retrofit-2026-09-04/` validator failures. |
| MR-024 | fixed | `README.md:200` now points to the committed `10_DASHBOARD/output/checkyourself-dogfood-dashboard-live-20260612.png`, which exists and is a PNG. |
| MR-025 | fixed | `README.md:190` now describes the shipped thin local stdio MCP wrapper and links to the current CLI/MCP docs; it no longer calls MCP future work. |
| MR-028 | fixed | `README.md:68,253` now says command-line use is not required while accurately naming the optional Python CLI and validator. |

## Acceptance evidence

- `python3 tools/checkyourself.py scan . --deep --ci --no-write` — **exit 0**;
  231 files scanned, zero open P0/P1/P2/P3 findings, one path-scoped
  suppression (`CY-CODE-001`).
- `python3 tools/checkyourself.py coverage --check 02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-coverage.json`
  — **exit 0**, `Coverage complete`.
- `python3 tools/checkyourself.py score --findings <(python3 tools/checkyourself.py scan . --deep --ci --format json --no-write) --coverage 02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-coverage.json --no-history`
  — **exit 0**, `Score: 100 (high confidence, raw 100)`.
- `python3 tools/validate_public.py` — **exit 1** for the known baseline only:
  `_retrofit-2026-09-04/FINDINGS-luna-a.md:270 -> target.md "title"` and
  `_retrofit-2026-09-04/FINDINGS-luna-b.md:21 ->
  10_DASHBOARD/output/checkyourself-dogfood-dashboard-screenshot.png`.
  Per the W8 brief, both are orchestrator-owned and ignored.
- `python3 -m pytest tests/ -q` — **exit 1** for the same known baseline
  validator failure; 89 tests passed and 53 subtests passed.

## Test tail

```text
FAILED tests/test_validate_public.py::ValidatePublicTests::test_real_repository_passes_validation
1 failed, 89 passed, 53 subtests passed in 25.76s
```

## Exact changed-file list

- `README.md`
- `02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-recheck-report.md`
- `10_DASHBOARD/output/TASTECHECK-PASS.md`
- `_retrofit-2026-09-04/WAVE8-REPORT.md`

Verified in scope but unchanged because already aligned:

- `checkyourself.manifest.json`
- `LICENSE`
- `NOTICE.md`

The required `td usage --new-session` call was attempted, but this checkout has
no `td` database (`run 'td init' first`); `td init` was not run.

## IMPROVEMENTS

1. **Separate orchestrator markdown from public validation.** WHY: the required
   validator and full suite remain red on two intentionally incomplete retrofit
   links, obscuring the W8 public-surface result. FIX: exclude
   `_retrofit-*` from public-link validation or give it a separate artifact
   contract.
2. **Refresh generated proof receipts from a reproducible runner.** WHY: this
   wave had to preserve the existing dashboard measurement receipt while
   updating repository-level evidence, because the original live gate runner
   is not present in this checkout. FIX: add a local, dependency-free receipt
   command that regenerates the dashboard and README proof with a timestamp.
