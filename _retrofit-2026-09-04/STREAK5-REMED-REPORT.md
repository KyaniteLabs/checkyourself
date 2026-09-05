# Streak 5 Remediation Report

Status: DONE_WITH_CONCERNS

Date: 2026-09-05
Scope: SOL's two post-ASTRA laundering exploits
Git: no commit or push performed

## Finding status

| Finding | Status | Evidence |
|---|---|---|
| Irrelevant receipt laundering | CLOSED | `tools/checkyourself.py:1542-1699` now requires the verifier issuer, canonical surface ID, source revision, command, claim, result, issuance time, content hash, and a binding hash. Coverage passes the expected surface and rejects duplicate receipt IDs across all rows. Caller-authored provenance without the verifier contract becomes Unknown. |
| Finding linked only to a fixed ID | CLOSED | `tools/checkyourself.py:2283-2303` intersects coverage linkage with unresolved finding IDs. An empty live set is independently scored and marks the category as blocked evidence, preserving the critical cap and manual-evidence request. |

## Receipt path

The native `receipt` command and read-only MCP `receipt_issue` tool issue one
receipt for one canonical surface:

```text
python3 tools/checkyourself.py receipt --root ROOT --reference ARTIFACT \
  --surface-id S11 --source-revision REVISION --source-state STATE \
  --command COMMAND --claim CLAIM --result RESULT --out RECEIPT.json --format json
```

`receipt_sha256` is a canonical SHA-256 over the reference, artifact hash,
surface, revision, command, claim, provenance, result, issuer, and issuance
time. The verifier recomputes it before awarding evidence credit. A coverage
row may optionally declare `claim`; when present, the receipt claim must match
it. A receipt ID can be consumed only once across evidence and delegation
receipts in one coverage artifact.

## Required regression probes

- Authentic but irrelevant `README.md`, correct content hash, and only
  caller-authored `origin`/`source_state`/`result`, reused for every `Pass` row:
  **29/100, low confidence**, with caps `84` and `90`.
- The same caller-authored receipt reused for every `NotApplicable` delegation
  row: **29/100, low confidence**, with caps `84` and `90`.
- `S07` marked `Finding`, linked only to fixed `F-FIXED-ISOLATION`, with the
  other rows backed by valid bound receipts: **82/100, low confidence**, with
  the `84` critical-evidence cap; `CY-COVERAGE-S07` is scored and C1 remains in
  `manual_evidence_needed`.

## Acceptance evidence

- `python3 -m pytest tests/ -q` — **123 passed, 88 subtests passed**.
- `python3 tools/validate_public.py .` — **OK: public CheckYourself validation passed**.
- `python3 -m py_compile tools/checkyourself.py tests/test_checkyourself_cli.py tools/validate_public.py` — passed.
- `git diff --check` — passed.
- Receipt generation, receipt schema validation, tampered binding rejection,
  caller-authored Pass/NotApplicable laundering, and fixed-ID linkage are
  covered in `tests/test_checkyourself_cli.py:1968-2078`.

## Files changed

- `tools/checkyourself.py`
- `schemas/coverage.schema.json`
- `schemas/receipt.schema.json`
- `tests/test_checkyourself_cli.py`
- `docs/cli.md`
- `docs/mcp.md`
- `skills/checkyourself/SKILL.md`
- `_retrofit-2026-09-04/STREAK5-REMED-REPORT.md`

## Concerns

The minimal receipt issuer provides tamper-evident binding and a distinct
verifier-issued path, but it does not independently execute the recorded
command or cryptographically attest to the operator identity. The receipt
contract therefore closes the two specified laundering paths while leaving the
independent challenge-runner boundary explicitly outside this streak.

`td usage --new-session` could not run because this checkout has no initialized
`td` database. No task-tracker state was changed.

## IMPROVEMENTS

1. Improve receipt authority. WHY: the requested minimal issuer hashes caller-
   supplied result text and does not prove that the command ran. FIX: add a
   separately controlled challenge runner that executes approved checks and
   emits receipts from captured stdout, exit status, and source revision.
2. Improve receipt freshness. WHY: source revision is recorded but not compared
   with the current project state during scoring. FIX: add an optional
   verifier-checked repository revision and invalidate receipts after relevant
   source changes.
3. Improve operator setup. WHY: the required `td` session command cannot run in
   an uninitialized checkout. FIX: provide a repository-local, non-destructive
   `td init` bootstrap or an explicit task-registration fallback.
