# WAVE 10 Report — W8 Public Truth and Current Proof

Status: DONE_WITH_CONCERNS

## Scope

The inline brief selected the register's W8 rows MR-011, MR-012, MR-024,
MR-025, and MR-028. The owner ruling was applied as final: Apache-2.0 is the
license of record, `LICENSE` is the legal artifact, and `NOTICE.md` follows
Apache practice. No license decision was made. No Git commands, installs, or
network calls were used.

## Per-row status

| Row | Status | Evidence |
|---|---|---|
| MR-011 | fixed | `README.md:7,268,283` uses Apache-2.0 in the badge, FAQ, and license section. `checkyourself.manifest.json:5`, `LICENSE:1-2`, and `NOTICE.md:5` agree. A targeted probe found no `MIT` claim in the W8 license surfaces. |
| MR-012 | fixed with known baseline | `02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-recheck-report.md:3-17,33-49` and `10_DASHBOARD/output/TASTECHECK-PASS.md:1,10-12,25,43-52` are dated 2026-09-04, record current proof, and explicitly label the two orchestrator-owned retrofit-link failures. |
| MR-024 | fixed | `README.md:198-200` points to the committed dashboard image; `file` verifies `10_DASHBOARD/output/checkyourself-dogfood-dashboard-live-20260612.png` is a 1280x4160 PNG. |
| MR-025 | fixed | `README.md:190` describes the shipped thin local stdio MCP wrapper and links to `docs/cli.md` and `docs/mcp.md`; `docs/mcp.md:3-10` documents the shipped local server and shared CLI logic. |
| MR-028 | fixed | `README.md:68` says no command line is required, while `README.md:180-188,252-253` accurately identifies the optional Python CLI and validator. |

## Acceptance evidence

The register's W8 acceptance commands were run independently so the known
validator failure did not prevent the required full-suite check:

- `python3 tools/validate_public.py` — **exit 1**, only for the known
  orchestrator-owned links:
  `_retrofit-2026-09-04/FINDINGS-luna-a.md:270 -> target.md "title"` and
  `_retrofit-2026-09-04/FINDINGS-luna-b.md:21 ->
  10_DASHBOARD/output/checkyourself-dogfood-dashboard-screenshot.png`.
- `python3 -m pytest tests/ -q` — **exit 1** because of the same known
  validator baseline; **89 passed, 53 subtests passed, 1 failed**.

## Test tail

```text
FAILED tests/test_validate_public.py::ValidatePublicTests::test_real_repository_passes_validation
1 failed, 89 passed, 53 subtests passed in 25.85s
```

## Exact changed-file list

- `_retrofit-2026-09-04/WAVE10-REPORT.md` (created by this worker)

W8 product files were verified and unchanged because they were already aligned:

- `README.md`
- `checkyourself.manifest.json`
- `LICENSE`
- `NOTICE.md`
- `02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-recheck-report.md`
- `10_DASHBOARD/output/TASTECHECK-PASS.md`
- `10_DASHBOARD/output/checkyourself-dogfood-dashboard-live-20260612.png`

## IMPROVEMENTS

1. **Separate retrofit markdown from public-link validation.** WHY: the
   required validator and full suite remain red on two explicitly exempt
   retrofit links, obscuring the W8 product-surface result. FIX: exclude
   `_retrofit-*` from public validation or give it a separate historical
   artifact contract.

2. **Generate both proof receipts from one reproducible command.** WHY: the
   existing receipts require manual date and scan-count refreshes. FIX: add a
   dependency-free receipt command that runs the scan, coverage, score, and
   receipt rendering from one captured evidence set.
