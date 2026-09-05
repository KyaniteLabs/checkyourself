# WAVE 2 Report — Make Schemas Prove Their Contracts

Status: DONE_WITH_CONCERNS

## Per-row status

| Row | Status | Evidence |
|---|---|---|
| MR-003 | fixed | `validate_json_schema` now executes `oneOf`/`anyOf`/`allOf`/`not`, `const`, `additionalProperties`, array/string constraints, and numeric exclusive bounds. Unsupported schema keywords are detected recursively and fail closed instead of being silently ignored. Dashboard empty and garbage artifacts are covered by CLI and MCP regression tests. |
| MR-004 | fixed | `schemas/checkyourself-report.schema.json` now requires the complete report section contract: executive summary, app purpose, detected stack, unknowns, score breakdown/caps, canonical coverage, findings, evidence table, remediation backlog, approval batch/prompts, full remediation path, deferred items, questions, learning seeds, and dashboard handoff. A golden report validates, and omission of every required section fails. |

## Acceptance evidence

- `python3 -m pytest tests/test_checkyourself_cli.py -q -k 'dashboard_one_of or golden_dashboard_and_report or report_requires_every_documented_section'` — **passed**: 3 tests, 25 subtests; empty and garbage dashboard fixtures fail, compact/template dashboard fixtures and the golden report pass through CLI and MCP, and every required report section is omission-tested.
- `python3 -m pytest tests/ -q` — **not green**: 63 passed, 33 subtests passed, 1 failed.

## Full-suite test tail

The only failure is outside W2:

`ValidatePublicTests.test_real_repository_passes_validation`

The public validator reports existing broken local links at `README.md:200`, `_retrofit-2026-09-04/FINDINGS-luna-a.md:270`, and `_retrofit-2026-09-04/FINDINGS-luna-b.md:21`. The first belongs to later public-asset repair; the latter two are orchestrator-owned retrofit artifacts. No W2 change was made for these links.

## Files changed

- `tools/checkyourself.py`
- `schemas/checkyourself-report.schema.json`
- `tests/test_checkyourself_cli.py`
- `_retrofit-2026-09-04/WAVE2-REPORT.md`

No installs, network calls, git commands, or changes outside W2 scope and this report were made.

## IMPROVEMENTS

1. Add a pre-wave full-suite baseline receipt. The required suite exposed inherited public-link failures only after implementation; recording the baseline first would make regression ownership immediately obvious.
2. Keep a checked-in golden report fixture beside the schema. The current regression fixture lives in the CLI test module, so other validators cannot reuse the same complete contract example without duplicating it.
