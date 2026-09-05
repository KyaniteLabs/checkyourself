# Semantic Vacuity and Custody Remediation Report

Status: DONE_WITH_CONCERNS

Scope: S11-1 semantic vacuity, S11-2 local integrity binding truth, and S11-3
symbol-to-test annotations. No commit or push was performed.

## Finding status

| Finding | Status | Evidence |
|---|---|---|
| S11-1 — Executed does not mean probative | CLOSED | `tools/checkyourself.py` now applies verifier-owned contracts to all 20 canonical surfaces. Definitions require positive output assertions; `true`, `false`, `echo`, `printf`, and print-only commands fail closed; broad regexes are tested against empty/echo fixtures; output token minimums are enforced at execution and re-execution. S11 additionally requires a recognized test runner and numeric result count. S12-S14 require a non-empty artifact; S19 requires JSON `status` and `findings` assertions. |
| S11-2 — HMAC custody boundary | CLOSED AS DOCUMENTATION/TRUTH FIX | The key path is `.checkyourself/local-integrity-binding.key` and the receipt field is `local_integrity_hmac`. Code and docs describe project-local tamper evidence only; they do not claim independent issuance or operator identity. Full external custody remains future work. |
| S11-3 — Symbol-to-test navigation gap | CLOSED | `tests/test_checkyourself_cli.py` now contains a short map for subprocess/CLI-indirect verifier symbols, including challenge execution, HMAC validation, semantic challenge validation, and scoring. |

## Regression evidence

- `true` challenge: `FAIL`, with vacuous-command and missing-semantic-contract reasons; its receipt cannot produce high confidence or full score.
- Echo-only challenge: `FAIL`, even with a positive regex assertion.
- `.*` assertion: rejected as vacuous against empty/echo fixtures.
- Genuine S11 dogfood: `PASS`; `python3 tools/checkyourself.py challenge --surface S11 --format json` completed with a numeric pytest result and `local_integrity_hmac`.
- Build artifact contract: missing artifact fails; a non-empty artifact under `build/` passes.
- Structured analysis contract: S19 without `status` and `findings` assertions fails.
- `python3 -m pytest tests/ -q`: **145 passed, 88 subtests passed**.
- `python3 tools/validate_public.py .`: **OK: public CheckYourself validation passed**.
- Challenge configuration validation: `valid: true`.
- `git diff --check`: clean.

## Files changed

- `tools/checkyourself.py`
- `schemas/challenges.schema.json`
- `.checkyourself/challenges.json`
- `tests/test_checkyourself_cli.py`
- `docs/cli.md`
- `_retrofit-2026-09-04/RUNNER-HARDEN-REPORT.md`

## Boundary and remaining concern

The local integrity binding detects edits to project-local receipts when the
same project key is available. Because the key is stored inside the inspected
project and controlled by the same local principal, it is not independent
attestation. A separately controlled external issuer or challenge service is
still required for that stronger guarantee.

## IMPROVEMENTS

1. Move receipt signing to externally controlled custody. WHY: the local key
   cannot separate the caller from the issuer. FIX: add a future verifier
   process or service with a key outside project write authority.
2. Replace marker-based S11 runner recognition with reviewed adapters. WHY:
   command text can mention a runner without proving the invocation path.
   FIX: define stack-specific runner adapters that capture the runner's native
   result schema while retaining the verifier-owned pass-count contract.
3. Record artifact digests in executed receipts. WHY: the current artifact
   contract verifies a non-empty path at execution time but does not preserve a
   separate artifact digest. FIX: bind artifact path and digest into the
   receipt and re-check them on replay.
