# W4 Report — truthful backlog and diff semantics

## Scope

Implemented only W4 rows MR-005, MR-006, and MR-017 in the scoped CLI, plan, and test files. No git commands, installs, or network calls were used.

## Per-row status

| Row | Status | Evidence |
|---|---|---|
| MR-005 | PASS | `diff` now records identity-aware `newly_open`, `reopened`, and `severity_escalated` events; `regression` gates on those events as well as aggregate P0/P1 count increases. Equal-count open P1 replacement is covered by `test_diff_gates_equal_count_p1_replacement`; the probe produced `regression: true` with unchanged P1 counts and `--ci` exit 1. |
| MR-006 | PASS | Backlog and next outputs now name the lexical slice `highest_severity_batch` and include `batch_basis` with `safety_analysis: not performed`; the old schema-required fields remain compatibility aliases. Documentation and CLI/MCP descriptions no longer claim safety/dependency ranking. |
| MR-017 | PASS | Open-to-resolved status changes remain in `resolved` using the current resolved finding and are detailed in `status_changes`; the finding is removed from `unchanged`. Covered by `test_diff_reports_status_only_resolution`. |

## Acceptance evidence

- Focused W4 tests: `4 passed, 53 deselected in 0.49s`.
- Direct probes passed for equal-count P1 replacement, open-to-fixed resolution, and `highest_severity_batch` output.
- Text-rendering probe passed: `Next batch: F-001`.
- Full required command: `python3 -m pytest tests/ -q`.
- Full-suite result: `1 failed, 73 passed, 33 subtests passed in 14.90s`.
- The failure is the known public-validator link baseline: `README.md:200` points to the missing dashboard screenshot, and two broken links are inside the orchestrator-owned `_retrofit-2026-09-04/` artifacts. README/artifact repair is outside W4 scope and belongs to later public-surface work.

## Test tail

```text
FAILED tests/test_validate_public.py::ValidatePublicTests::test_real_repository_passes_validation
1 failed, 73 passed, 33 subtests passed in 14.90s
next text output: PASS (Next batch: F-001)
```

## Exact changed-file list

- `_retrofit-2026-09-04/WAVE4-REPORT.md`
- `tools/checkyourself.py`
- `docs/agent-access-cli-plan.md`
- `tests/test_checkyourself_cli.py`

## IMPROVEMENTS

1. **Replace the schema-required batch aliases in a future schema revision.** Why: `first_approval_batch` and `next_approval_batch` still look safety-ranked to older consumers even though the current output is truthful. Proposal: version the backlog/next schemas around `highest_severity_batch` and make the compatibility window explicit.
2. **Add a repository-level acceptance fixture for public-validator exclusions.** Why: the full suite mixes out-of-scope retrofit artifacts with the public README gate, obscuring which wave owns the failure. Proposal: define a validator fixture or exclusion contract so wave acceptance reports isolate owned failures.
