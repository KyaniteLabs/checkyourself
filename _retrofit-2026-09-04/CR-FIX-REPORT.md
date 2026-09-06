# Code-Review Finding Fix Report

Date: 2026-09-05
Scope: `CY-REVIEW-001`, `CY-REVIEW-002`, and `CY-REVIEW-003`

## Result

All three P1 findings are fixed with focused regressions. No commit, push, install, or network access was used.

## Fixes

- `CY-REVIEW-001`: `_challenge_result` now resolves each asserted artifact and requires its real path to remain under the resolved project root. A symlinked parent that points outside the project is rejected before the artifact can earn a pass.
- `CY-REVIEW-002`: challenge execution now uses `Popen(..., start_new_session=True)`. A timeout sends `SIGTERM` to the complete process group, waits briefly, then sends `SIGKILL` if needed. The timeout state is preserved in the receipt and assertion result.
- `CY-REVIEW-003`: `schemas/coverage.schema.json` now accepts either the existing verifier receipt or the executed challenge receipt, including `local_integrity_hmac`, `captured_output_digest`, `semantic_output_digest`, and `source_revision`. Existing scoring already binds an executed receipt through `evidence_receipts` plus the matching `evidence_reviewed` capture reference, so no new attach command was needed.

## Repro outcomes

- Symlinked-parent artifact repro (`root/linked -> external`, `linked/proof.txt`): now returns `FAIL` with `artifact path escapes the project root`.
- Descendant-timeout repro (child spawns a grandchild sleeper): now returns a timed-out failure and the grandchild cannot create its post-timeout marker.
- S11 executed receipt: `validate --kind coverage` now returns valid, and `score --coverage` awards C5 with `verified_evidence` bound to the captured output.

## Verification

- Focused regressions: 3 passed.
- `python3 -m pytest tests/ -q`: **PASS**, 152 tests and 88 subtests.
- `python3 tools/validate_public.py .`: **PASS**.
- `python3 -m py_compile tools/checkyourself.py tests/test_checkyourself_cli.py`: **PASS**.
- `git diff --check`: **PASS**.

## Changed files

- `tools/checkyourself.py`
- `schemas/coverage.schema.json`
- `tests/test_checkyourself_cli.py`
- `_retrofit-2026-09-04/CR-FIX-REPORT.md`

## IMPROVEMENTS

1. Improve challenge capture limits. Why: review evidence identified unbounded `capture_output` as a remaining resource risk. Fix: stream stdout/stderr into bounded files and record truncation explicitly.
2. Improve receipt diagnostics. Why: aggregate re-execution can still lose fresh stdout/stderr when a receipt mismatch occurs. Fix: retain bounded re-execution diagnostics in the verification result.
3. Improve challenge environment isolation. Why: challenge subprocesses still inherit the full parent environment. Fix: add an opt-in allowlisted environment mode for untrusted project reviews.
