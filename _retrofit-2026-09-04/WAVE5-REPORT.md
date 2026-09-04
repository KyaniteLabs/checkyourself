# W5 Report — malformed-input and configuration hardening

## Scope

Implemented only W5 rows MR-013, MR-014, MR-015, MR-016, MR-018, MR-019, MR-023, and MR-035. No git commands, installs, network calls, or out-of-scope wave changes were used.

## Per-row status

| Row | Status | Evidence |
|---|---|---|
| MR-013 | PASS | Non-object `package.json` values now produce a stack signal instead of `.get()` traceback. Regression coverage exercises `null`, array, and boolean roots. |
| MR-014 | PASS | JSON/YAML suppression shapes and field types are validated; invalid configs expose `config_error`, emit stable `CY-CONFIG-003`, and apply no suppressions. |
| MR-015 | PASS | `.gitignore` now parses comment lines and evaluates ordered, anchored, basename, wildcard, negation, and directory-aware rules. Tests cover comment false positives and nested ignored env files. |
| MR-016 | PASS | `is_env_example_name` is the shared classifier for scanning and missing-example checks. `.env.local.example` and other supported variants no longer create `CY-ENV-003`. |
| MR-018 | PASS | Non-object and malformed coverage roots return structured coverage errors without tracebacks. Existing CLI/MCP invalid-coverage tests remain green. |
| MR-019 | PASS | MCP arguments are validated against each advertised input schema before conversion. Wrong scalar types and `max_files: 0` return JSON-RPC `-32602`; optional score `coverage: null` remains an explicit core-artifact validation path for W1 compatibility. |
| MR-023 | PASS | Supplied coverage rows must carry canonical `id`, `surface`, and `category` fields; duplicate, unknown, mismatched, missing-field, and extra structural rows are rejected. |
| MR-035 | PASS | Top-level `--help` now lists all 12 shipped subcommands instead of routing to legacy scan help. |

## Acceptance evidence

- `python3 -m py_compile tools/checkyourself.py tests/test_checkyourself_cli.py` — PASS.
- Focused CLI suite — `64 passed, 36 subtests passed in 14.23s`.
- Required full suite — `1 failed, 80 passed, 38 subtests passed in 15.32s`.
- The single failure is `ValidatePublicTests.test_real_repository_passes_validation`. Its three broken links are the known retrofit evidence links plus the pre-existing README dashboard screenshot link (`README.md:200`, MR-024/W8 scope). No W5 code or test failure occurred.

## Test tail

```text
FAILED tests/test_validate_public.py::ValidatePublicTests::test_real_repository_passes_validation
1 failed, 80 passed, 38 subtests passed in 15.32s
```

## Exact changed-file list

- `_retrofit-2026-09-04/WAVE5-REPORT.md`
- `tools/checkyourself.py`
- `tests/test_checkyourself_cli.py`

## IMPROVEMENTS

1. **Give the public validator an explicit retrofit-artifact policy.** Why: the required full suite remains red because orchestrator evidence markdown is scanned with public-link rules. Proposal: define a narrow artifact exclusion or separate evidence validator so wave acceptance isolates owned failures.
2. **Replace the hand-rolled YAML subset with a documented config contract.** Why: the scanner must reject malformed shapes without adding a dependency, so supported YAML syntax remains intentionally narrow. Proposal: publish the accepted subset and add fixtures for escaped comments, inline values, and future schema changes.
