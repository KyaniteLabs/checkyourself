# WAVE 1 Report — Fail Closed at the Score Trust Boundary

Status: DONE_WITH_CONCERNS

## Per-row status

| Row | Status | Evidence |
|---|---|---|
| MR-001 | fixed | Coverage-backed scoring now validates supplied coverage before calculating category state or producing a score. Invalid/null status, null artifact, duplicate IDs, unknown IDs, mismatched canonical surfaces, mismatched categories, invalid row shapes, and invalid evidence-array shapes are rejected. Missing canonical rows remain explicitly incomplete rather than being treated as invalid, so partial but structurally valid evidence retains its low-confidence estimate behavior. |

No W1 rows were parked. No changes were made for W2–W10.

## Acceptance evidence

- `python3 -m pytest tests/test_checkyourself_cli.py -q -k 'score_rejects_invalid_coverage or coverage_backed_score_blocks_thin_pass_gaming or coverage_backed_full_evidence_reaches_high_confidence'` — **passed**: 3 tests, 6 subtests; invalid, null, duplicate, unknown-ID, and mismatched-category fixtures rejected through both CLI and MCP; valid partial and full coverage behavior preserved.
- `python3 -m pytest tests/test_checkyourself_cli.py -q` — **passed**: 44 tests, 6 subtests.
- `python3 -m pytest tests/ -q` — **not green**: 60 passed, 8 subtests passed, 1 failed.

## Full-suite test tail

The only full-suite failure is outside W1:

`ValidatePublicTests.test_real_repository_passes_validation`

The public validator reports existing broken links in `README.md:200`, `_retrofit-2026-09-04/FINDINGS-luna-a.md:270`, and `_retrofit-2026-09-04/FINDINGS-luna-b.md:21`. Those paths belong to later public-truth/validator work and were not changed in this wave.

## Files changed

- `tools/checkyourself.py`
- `tests/test_checkyourself_cli.py`
- `_retrofit-2026-09-04/WAVE1-REPORT.md`

No dependency installs, network calls, git commands, or changes outside W1 scope and this report were made.

## IMPROVEMENTS

1. Make the full-suite baseline explicit before wave execution. The required suite exposed a pre-existing public-validation failure only after W1 implementation; record baseline failures so wave acceptance distinguishes regressions from inherited debt.
2. Centralize a reusable canonical coverage fixture factory for CLI and MCP tests. The new tests currently load the executable module in each helper; a shared fixture would reduce setup duplication while keeping the canonical surface list authoritative.
