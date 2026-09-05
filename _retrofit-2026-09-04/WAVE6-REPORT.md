# WAVE 6 Report — Align Discovered Evidence with Proven Evidence

Status: DONE_WITH_CONCERNS

## Scope

Implemented only W6 rows MR-022 and MR-027 in the scoped CLI, test, and plan
files. No installs, network calls, Git commands, or changes outside W6 and this
report were made.

## Per-row status

| Row | Status | Evidence |
|---|---|---|
| MR-022 | fixed | `tools/checkyourself.py:1730-1752` now treats detected test and CI paths as `Unknown`, records the detected candidates, and requires focused execution or CI parse/success receipts. Empty test files and malformed CI files are covered by `test_scan_derived_presence_is_not_proof_of_tests_or_ci`; neither can produce `Pass`. |
| MR-027 | fixed | `tests/test_checkyourself_cli.py` now covers all documented caps (`test_scoring_contract_covers_all_documented_caps`), justified NotApplicable scoring, negative machine-schema artifacts through CLI and MCP, timestamp-normalized scan/score/backlog goldens, emitted-object schema validation, and the CLI/MCP scan→score→validate pipeline. Existing W4 transition and W3 read-only tests remain in the full suite. `docs/agent-access-cli-plan.md:111-114,325-342` records the presence-versus-proof rule and the implemented contract matrix. |

## Acceptance evidence

- Focused W6 command:
  `python3 -m pytest tests/test_checkyourself_cli.py -q -k 'scoring_contract_covers_all_documented_caps or not_applicable_scoring_preserves_its_weight or scan_derived_presence_is_not_proof_of_tests_or_ci or validate_rejects_empty_machine_artifacts_in_cli_and_mcp or cli_outputs_are_deterministic_goldens_after_timestamp_normalization or cli_and_mcp_scan_score_validate_pipeline'`
  — **passed**: 6 tests, 15 subtests.
- Required command:
  `python3 -m pytest tests/ -q`
  — **86 passed, 53 subtests passed, 1 failed**.

## Full-suite test tail

```text
FAILED tests/test_validate_public.py::ValidatePublicTests::test_real_repository_passes_validation
1 failed, 86 passed, 53 subtests passed in 17.84s
```

The failure is inherited public-validator link debt, not a W6 failure:

- `README.md:200` points to the missing dashboard screenshot (`MR-024/W8`).
- `_retrofit-2026-09-04/FINDINGS-luna-a.md:270` contains the known orchestrator-artifact link failure.
- `_retrofit-2026-09-04/FINDINGS-luna-b.md:21` contains the known orchestrator-artifact link failure.

Per the brief, these links were not chased.

## Exact changed-file list

- `tools/checkyourself.py`
- `tests/test_checkyourself_cli.py`
- `docs/agent-access-cli-plan.md`
- `_retrofit-2026-09-04/WAVE6-REPORT.md`

The required `td usage --new-session` call was attempted, but this checkout has
no `td` database (`run 'td init' first`); `td init` was not run.

## IMPROVEMENTS

1. Record the full-suite baseline before each wave. The actual friction was that
   inherited README and retrofit link failures remain mixed into wave acceptance;
   a baseline diff would make ownership immediate.
2. Put the W6 contract matrix in a shared fixture module once the test suite grows
   further. The current tests repeat CLI/MCP artifact setup, which increases the
   chance that future verbs gain only one-sided coverage.
