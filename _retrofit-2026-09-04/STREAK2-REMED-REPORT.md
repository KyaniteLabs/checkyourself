# Streak-2 Remediation Report

Status: DONE

## Scope

Closed the DSV4 round-2 proof gaps for negative paths, corrupted receipts,
report validation, interrupted writes, and line-ending diffs. No installs,
network access, commits, or pushes.

## Changes

- Added strict standard-JSON parsing. `NaN`, `Infinity`, overflowed numbers,
  malformed JSON, and unreadable artifact files now fail closed.
- Added finite guards for scoring weights and severity penalties.
- Rejected non-object findings entries and missing findings/backlog arrays
  instead of silently scoring or batching them as empty.
- Made generated text writes same-directory atomic writes with flush/fsync and
  cleanup on interruption. Corrupt score-history shapes are preserved as
  `.corrupt.bak` before recovery.
- Added tests for Unicode, empty, huge, CRLF/LF/mixed-line-ending, malformed,
  partial, and non-finite inputs; score-to-report schema round trips; invalid
  report mutations; MCP parse errors; and simulated write interruptions.

## Verification

`python3 -m pytest tests/ -q`

```text
109 passed, 86 subtests passed in 26.25s
```

`python3 tools/validate_public.py`

```text
OK: public CheckYourself validation passed
```

`python3 -m py_compile tools/checkyourself.py tests/test_checkyourself_cli.py`

```text
passed
```

`git diff --check`

```text
passed
```

## Evidence map

| DSV4 gap | Proof |
|---|---|
| NaN/Inf scoring and schema paths | `test_nonfinite_numbers_are_rejected_across_schema_and_scoring_paths` plus strict parser and runtime guards. |
| Malformed and corrupted receipts | `test_malformed_json_fails_closed_for_cli_artifact_consumers`, `test_corrupt_receipts_do_not_become_false_empty_artifacts`, MCP parse coverage, and expanded score-history recovery test. |
| Coverage mid-write | Truncated coverage input returns structured code 2 and never emits a score. |
| Score-to-report round trip | `test_score_to_report_round_trip_and_invalid_mutations_fail_schema` validates a report assembled from live score/backlog output and rejects missing, out-of-range, and invalid contract fields. |
| Interrupted writes | `test_atomic_generated_writes_preserve_previous_contents_on_interruption` proves the existing destination remains intact and temporary files are removed when fsync or replace fails. |
| Line-ending truthfulness | `test_diff_ci_treats_line_endings_as_noop_and_reports_real_changes` treats CRLF/LF/mixed formatting as semantic no-op while gating a real P1 addition. |
| Unicode/empty/huge edges | `test_unicode_empty_and_huge_strings_survive_scan_and_receipt_commands` covers scan, score, backlog, next, and diff. |

## Scope notes

The existing worktree contains unrelated user-owned retrofit edits; they were
left untouched. The `td` database is not initialized in this checkout, so
`td usage --new-session` could not produce a task receipt. No task database was
created.

## IMPROVEMENTS

1. **Add a single acceptance-receipt command.** WHY: the final proof currently
   requires separate pytest, public-validation, compile, and diff-check
   commands. FIX: add one dependency-free command that runs and records all
   streak acceptance gates without changing repository state.

2. **Expose a first-class report builder.** WHY: the round-trip test assembles
   a report shell from score/backlog output because report generation remains
   an agent-side contract. FIX: add a small deterministic report composition
   API or explicitly document the shell boundary so consumers can reproduce
   the same contract without test-only assembly.
