# WAVE 3 Report — Restore Scanner Completeness and Safe Writes

Status: DONE_WITH_CONCERNS

## Per-row status

| Row | Status | Evidence |
|---|---|---|
| MR-002 | fixed | `scan` and `diagnostic` now emit to stdout without creating Markdown or JSON files unless `--out`/`--json` is explicit. `score` no longer creates score history by default; `--history` is explicit. `test_audit_defaults_leave_fixture_tree_unchanged` and explicit-history coverage protect both paths. |
| MR-007 | fixed | File iteration now records oversized, unreadable, symlink-skipped, and file-cap-truncated paths in `scan_limits`; eligible content is read through the 2 MB file ceiling, and `scan_limits.incomplete` is true whenever coverage is partial. Markdown/text output also warns about incomplete scans. Oversized, file-cap, and post-previous-cap secret fixtures are covered. |
| MR-008 | fixed | `Dockerfile`, `Makefile`, and `Jenkinsfile` are classified as extensionless config basenames and enter the secret/config detectors. `test_extensionless_config_files_are_scanned_for_secrets` proves Dockerfile credential detection. |
| MR-009 | fixed | Test discovery now uses explicit test directories and conventional test filenames (`test_*.py`, `*_test.go`, `*.test.*`, `*.spec.*`, and related forms), so arbitrary filename substrings no longer count. `test_filename_substrings_do_not_create_test_evidence` proves `latest.py` remains a non-test. |
| MR-010 | fixed | `safe_write_text` checks every existing path ancestor for symlinks, while allowing only root-level OS path aliases used by macOS temporary directories. `test_scan_refuses_to_write_through_symlinked_parent` proves nested parent redirection is rejected. |

## Acceptance evidence

- Focused W3 regression command:
  `python3 -m pytest tests/test_checkyourself_cli.py -q -k 'audit_defaults or reports_oversized or reads_eligible or extensionless_config or filename_substrings or reports_truncation or refuses_to_write_through_symlink'`
  — **passed**: 7 tests.
- Required full-suite command:
  `python3 -m pytest tests/ -q`
  — **69 passed, 33 subtests passed, 1 failed**.
- The only failure is `ValidatePublicTests.test_real_repository_passes_validation`. It reports three inherited broken links: the pre-existing README dashboard image and two links in orchestrator-owned `_retrofit-2026-09-04/` markdown. README image repair is MR-024/W8 and is outside this wave; no W3 change was made for these links.

## Test tail

```text
69 passed, 33 subtests passed, 1 failed
FAILED tests/test_validate_public.py::ValidatePublicTests::test_real_repository_passes_validation
```

## Exact changed-file list

- `tools/checkyourself.py`
- `tests/test_checkyourself_cli.py`
- `_retrofit-2026-09-04/WAVE3-REPORT.md`

No installs, network calls, Git commands, or changes outside W3 scope and this report were made. The required `td usage --new-session` call could not initialize because the local `td` database is absent (`run 'td init' first`); no `td init` was run.

## IMPROVEMENTS

1. Record the full-suite baseline before each wave. The actual friction was an inherited README failure appearing alongside the known retrofit-link failures, which complicates ownership of the acceptance result. Capture baseline failures before implementation and compare the final tail against it.
2. Version the scan-limit contract with the next schema wave. W3 adds useful path-level incompleteness receipts, but the current scan schema does not require those additive fields. Add them to a schema version or make them required in the next contract-focused wave.
3. Bootstrap the repository task database in the worker harness. The actual friction was `td usage --new-session` failing before task tracking could start. Provision `.td` before dispatch or make the orchestrator report a ready tracker path.
