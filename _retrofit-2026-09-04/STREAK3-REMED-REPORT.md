# Streak 3 remediation report

## Result

Implemented the three SOL round-1 remediation families as executable tests and
kept the affected JSON/write behavior fail-closed.

## Coverage delivered

- Report contract: added `parse_report` and `regenerate_report`, then proved a
  validated report round-trips to byte-identical canonical JSON. The score and
  backlog outputs are also assembled into a report and checked through the
  public report validator, including invalid mutations.
- Atomic writes and recovery: exercised real subprocess termination at the
  atomic replace boundary, real directory permission denial, simulated write
  interruption cleanup, and termination during corrupt score-history recovery.
  The recovery test now allows the corrupt backup rename and terminates on the
  subsequent atomic replace, leaving the original backup intact and the temp
  file observable.
- JSON edge fixtures: covered UTF-8 BOM plus trailing whitespace in diff input,
  mixed line endings, `NaN`/infinities, and numeric overflow (`1e309`).

## Files

- `tools/checkyourself.py`: strict JSON BOM/non-finite handling and report
  parser/regenerator support.
- `tests/test_checkyourself_cli.py`: real report, subprocess/filesystem, and
  JSON edge-case regression tests.

## Verification

- `python3 -m pytest tests/ -q` — **113 passed, 86 subtests passed**.
- `python3 tools/validate_public.py .` — **OK: public CheckYourself validation passed**.
- `python3 -m py_compile tools/checkyourself.py tests/test_checkyourself_cli.py` — passed.
- `git diff --check` — passed.
- No installs, network access, or git commits performed.

## Remaining concern

The permission-denial test is skipped when executed as root because root can
bypass directory mode bits; it runs on the current non-root environment.

## IMPROVEMENTS

1. Add a portable non-root test runner for permission-denial coverage so the
   test cannot be skipped in privileged CI. Why: root execution bypasses the
   filesystem failure the test is meant to prove. Proposal: run this one test
   in a constrained non-root CI job or use a platform-supported privilege drop.
2. Expose report parse/regenerate through one documented CLI or library entry
   point. Why: the contract is currently exercised through the Python module
   boundary rather than a user-facing report command. Proposal: add a small
   explicit report-normalize verb with schema validation and `--out` opt-in.
