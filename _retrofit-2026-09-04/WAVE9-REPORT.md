# WAVE 9 Report — W8 Rows: Public Truth and Current Proof

Status: DONE_WITH_CONCERNS

## Scope

Implemented and re-verified only W8 rows MR-011, MR-012, MR-024, MR-025, and
MR-028. The owner ruling was applied as final: Apache-2.0 is the license of
record, `LICENSE` is the legal artifact, and `NOTICE.md` follows Apache
practice. No license decision was made. No installs, network calls, or Git
commands were used.

## Per-row status

| Row | Status | Evidence |
|---|---|---|
| MR-011 | fixed | `README.md:7,268,283` uses Apache-2.0 in the badge, FAQ, and license section. `checkyourself.manifest.json:5`, `LICENSE:1-2`, and `NOTICE.md:5` agree. A targeted README probe found no MIT claim. |
| MR-012 | fixed with known baseline | Both proof receipts are dated 2026-09-04 and now record the live 234-file scan, complete coverage, 100/high-confidence score, and the known validator/test baseline. |
| MR-024 | fixed | `README.md:200` points to `10_DASHBOARD/output/checkyourself-dogfood-dashboard-live-20260612.png`; the asset exists and is a 1280x4160 PNG. No replacement was needed. |
| MR-025 | fixed | `README.md:190` describes the shipped thin local stdio MCP wrapper and its local/no-hosted-API boundary. `docs/mcp.md` and `tools/checkyourself.py:mcp_tools`/`run_mcp_server` provide the implementation evidence. |
| MR-028 | fixed | `README.md:68,253` says command-line use is not required while naming the optional Python CLI and validator. `START_HERE.md:35` confirms the same boundary. |

## Acceptance evidence

- `python3 tools/validate_public.py && python3 -m pytest tests/ -q` — exit 1
  at public validation because of the two explicitly allowed,
  orchestrator-owned `_retrofit-2026-09-04/` links. The pytest command was
  also run independently.
- `python3 tools/validate_public.py` — exit 1 for only:
  `_retrofit-2026-09-04/FINDINGS-luna-a.md:270 -> target.md "title"` and
  `_retrofit-2026-09-04/FINDINGS-luna-b.md:21 ->
  10_DASHBOARD/output/checkyourself-dogfood-dashboard-screenshot.png`.
- `python3 -m pytest tests/ -q` — exit 1: 89 passed, 53 subtests passed, and
  one known failure caused by the same two retrofit links.
- `python3 tools/checkyourself.py scan . --deep --ci --no-write` — exit 0;
  234 files scanned, zero open P0/P1/P2/P3 findings, one suppressed
  `CY-CODE-001` detector-pattern finding.
- `python3 tools/checkyourself.py coverage --check
  02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-coverage.json` — exit 0;
  `Coverage complete`.
- `python3 tools/checkyourself.py score --findings <(python3
  tools/checkyourself.py scan . --deep --ci --format json --no-write)
  --coverage 02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-coverage.json
  --no-history` — exit 0; `Score: 100 (high confidence, raw 100)`.

## Test tail

```text
FAILED tests/test_validate_public.py::ValidatePublicTests::test_real_repository_passes_validation
1 failed, 89 passed, 53 subtests passed in 14.01s
```

## Exact changed-file list

- `02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-recheck-report.md`
  (refreshed current scan count from 231 to 234)
- `10_DASHBOARD/output/TASTECHECK-PASS.md` (refreshed current scan count from
  231 to 234)
- `_retrofit-2026-09-04/WAVE9-REPORT.md` (this report)

Verified in scope but unchanged because already aligned:

- `README.md`
- `checkyourself.manifest.json`
- `LICENSE`
- `NOTICE.md`
- `10_DASHBOARD/output/checkyourself-dogfood-dashboard-live-20260612.png`

## IMPROVEMENTS

1. **Keep generated proof tied to a reproducible command.** WHY: the receipts
   needed a manual scan-count refresh after the repository grew from 231 to
   234 scanned files. FIX: add a dependency-free command that regenerates both
   current proof receipts from the same scan, coverage, and score commands.

2. **Give retrofit evidence its own validator boundary.** WHY: the required
   public validator and full test suite remain red on two explicitly ignored
   retrofit links, obscuring the W8 product-surface result. FIX: exclude
   `_retrofit-*` from public-link validation or validate it with a separate
   historical-artifact contract.
