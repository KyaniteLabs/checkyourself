# Streak 11 Independent Review — SOL

Status: DONE_WITH_CONCERNS

HEAD reviewed: `a5ec5ae` on `retrofit/2026-09-04` (read-only review; no source changes).

## Acceptance chain

- `python3 -m pytest tests/ -q`: PASS — 139 tests and 88 subtests passed in 43.08s.
- `python3 tools/validate_public.py .`: PASS.

## Required verification probes

- Caller-issued receipts cannot reach high: PASS. The full-caller-evidence probe returned low confidence, incomplete coverage, and a score below 100.
- Executed receipt re-run mismatch: PASS. Changing excluded challenge input after issuance made C5 Unknown and reported a re-executed output-digest mismatch.
- Failing challenge creates a finding and cap: PASS. `CY-CHALLENGE-S11` was scored and the 74 cap applied.
- Timeout is receipted as FAIL: PASS. The bounded timeout receipt had `timed_out: true` and `status: FAIL`.

## Findings

### S11-1 — P1: Executed does not mean probative

The verifier owns process execution and recomputes the stored outcome, but it does not own or validate what a challenge proves. A fresh hostile-project probe configured all 20 committed challenges as the equivalent of `python -c pass`, supplied only `exit_zero: true`, and used the resulting EXECUTED receipts as coverage. The scorer returned:

- score: 100
- confidence: high
- coverage_complete: true
- caps: none
- manual evidence needed: none

This is a launch-readiness bypass. The runner proves that caller-authored commands ran consistently; it does not prove that any production surface was tested. Verification authority is therefore not verifier-owned end-to-end.

Smallest safe correction: require verifier-owned per-surface semantic contracts (minimum assertions and recognized evidence/result shapes), or cap generic/custom challenges until a trusted policy maps each command and assertion set to the claimed surface. Add the trivial-command 20-surface probe as a permanent adversarial test.

### S11-2 — P2: The HMAC issuer boundary is local-project ownership

The signing key lives at `.checkyourself/challenge-runner.key` inside the inspected project and is readable/writable by the same OS principal that controls the project and invokes scoring. Mode 0600 prevents other accounts from reading it, but does not separate the caller from the claimed verifier issuer. Fresh re-execution still adds useful integrity and catches stale or edited receipts; the HMAC does not establish independent verifier provenance.

Smallest safe correction: describe the HMAC as local run-integrity binding, not independent attestation, unless key custody moves to a verifier-owned location/process outside the assessed project and outside the caller's write authority.

## Coherence verdict

The implementation is materially stronger: fail-closed execution, argv-only commands, timeouts, output/config/source binding, fresh re-execution, failure-to-finding conversion, and caller-receipt caps all behaved correctly. The remaining gap is foundational rather than incidental: semantic authority stays with the project-authored challenge definition, so a reproducible no-op can receive full launch-ready credit.

## IMPROVEMENTS

1. Improve semantic challenge validation. WHY: the fresh no-op matrix earned a perfect high-confidence score. FIX: add verifier-owned per-surface minimum contracts and reject or cap vacuous commands/assertions.
2. Improve trust-boundary naming. WHY: a key stored in the caller-owned project cannot prove an independent issuer. FIX: rename/document it as local integrity binding or move custody outside the project.
3. Improve regression coverage discovery. WHY: codegraph reported no covering tests for several directly tested verifier symbols, making review navigation misleading. FIX: add explicit symbol-to-test annotations or enhance codegraph's Python indirect-call/test association.

FULLY-GREEN: no
