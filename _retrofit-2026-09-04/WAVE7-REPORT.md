# WAVE 7 Report — Harden the Public Validator

Status: DONE_WITH_CONCERNS

## Scope

Implemented only W7 rows MR-020, MR-021, and MR-037 in the scoped validator,
test, and report files. No installs, network calls, or Git commands were used.

## Per-row status

| Row | Status | Evidence |
|---|---|---|
| MR-020 | fixed | `tools/validate_public.py:187-229` now rejects required directories, special files, final/parent symlinks, and paths resolving outside the validated root. `tests/test_validate_public.py:40-57` covers a directory stand-in and an external required-file symlink without a traceback. |
| MR-021 | fixed | `tools/validate_public.py:432-469` rejects symlinked asset directories/files, enforces resolved containment, catches directory/read/stat failures, and applies `MAX_VALIDATED_FILE_BYTES` before hashing. `tests/test_validate_public.py:212-226` proves an external asset symlink is rejected and not hashed as a duplicate. |
| MR-037 | fixed | `tools/validate_public.py:327-429` parses balanced destinations, escaped punctuation, angle-bracket destinations, optional titles, and unescaped fragments before checking local targets. `tests/test_validate_public.py:142-159` covers quoted, angle-bracket, and escaped destinations. |

## Acceptance evidence

- `python3 -m pytest tests/test_validate_public.py -q` — **19 passed, 2 subtests passed, 1 inherited failure**.
- `python3 -m pytest tests/ -q` — **89 passed, 53 subtests passed, 1 inherited failure**.
- `python3 tools/validate_public.py` — fails only on the known public-link baseline: the missing W8 README screenshot and two links inside `_retrofit-2026-09-04/` orchestrator artifacts. The validator no longer reports the title as part of the destination; that artifact still points to a deliberately absent `target.md`.
- `python3 -m py_compile tools/validate_public.py tests/test_validate_public.py` — passed.

## Test tail

```text
FAILED tests/test_validate_public.py::ValidatePublicTests::test_real_repository_passes_validation
1 failed, 89 passed, 53 subtests passed in 11.19s
```

The failure is outside W7 code paths:

- `README.md:200` references the missing W8 dashboard screenshot.
- `_retrofit-2026-09-04/FINDINGS-luna-a.md:270` contains the known missing `target.md` example.
- `_retrofit-2026-09-04/FINDINGS-luna-b.md:21` references the same missing W8 screenshot.

## Exact changed-file list

- `tools/validate_public.py`
- `tests/test_validate_public.py`
- `_retrofit-2026-09-04/WAVE7-REPORT.md`

The required `td usage --new-session` call was attempted, but this checkout has
no `td` database (`run 'td init' first`); `td init` was not run.

## IMPROVEMENTS

1. **Separate orchestrator artifacts from public-link validation.** WHY: the
   full suite remains red on intentionally incomplete retrofit evidence and
   inherited W8 proof, obscuring whether validator changes pass. FIX: exclude
   `_retrofit-*` from the public surface or validate it with a separate artifact
   contract.
2. **Share one path-safety helper with every public validator.** WHY: required
   files and assets now enforce the same boundary, but future manifest or
   release checks could reintroduce `exists()`-only validation. FIX: route all
   public path checks through a single regular-in-root helper.
