# Runner Hardening Report

## Outcome

The stored `EXECUTED` receipt escape is closed without a commit or push. Score
verification now requires a local-integrity binding HMAC, re-executes the committed challenge,
and accepts the receipt only when the fresh output digest, exit state, timeout
state, execution state, and current source revision agree.

## Changes

- `tools/checkyourself.py`
  - creates or loads a 32-byte local integrity binding key at
    `.checkyourself/local-integrity-binding.key` with mode `0600`;
  - derives a per-invocation signing key from the local binding key and receipt
    `run_id`, then records it as `local_integrity_hmac` over the executed receipt fields;
  - computes `source_revision` before writing captures and
    `captured_output_digest` after writing each capture;
  - re-runs the committed argv with the committed cwd, `shell=False`, and
    timeout during score-time verification;
  - downgrades absent/invalid HMAC, stale source, capture edits, output drift,
    exit drift, timeout drift, or an unavailable command to `Unknown`.
- `.checkyourself/challenges.json`
  - makes the shipped S11 pytest output deterministic by replacing only its
    volatile elapsed-time footer before capture hashing.
- `tests/test_checkyourself_cli.py`
  - adds forged E1, missing/invalid HMAC, edited capture, and fresh
    re-execution mismatch regressions;
  - retains the genuine executed-receipt happy-path proof.
- `docs/cli.md`
  - documents the HMAC, two-phase hash, and score-time re-execution contract.

## Probe E1 post-fix

Observed result from the forged merged-definition receipt regression:

- the receipt had a valid shape, committed command, merged challenge digest,
  capture digest, source revision, and receipt binding hash;
- it had no valid local-integrity binding HMAC;
- score verification reported the evidence as `Unknown` and applied the
  evidence cap; it did not grant executed credit or high confidence.

The focused regression passed as part of the challenge tests. Invalid HMACs
also fail closed before any score-time subprocess is launched.

## Verification

- `python3 -m pytest tests/ -q` — **139 passed, 88 subtests passed**.
- `python3 tools/validate_public.py .` — **OK: public CheckYourself validation passed**.
- `python3 tools/checkyourself.py challenge --surface S11 --format json` —
  **complete: true**, **PASS**, exit code `0`, signed receipt, no findings.
- In-memory score using the live S11 receipt — **C5 Pass** with the capture in
  `verified_evidence`; score-time re-execution accepted the genuine receipt.
- Local integrity binding key and S11 capture/receipt remain ignored local artifacts; no commit
  or push was performed.

The local integrity binding is project-local tamper evidence. It does not prove
independent issuance or operator identity; full external custody remains future
work.

## IMPROVEMENTS

- Add a reusable deterministic-output policy for commands with volatile timing.
  WHY: the first genuine S11 re-check exposed pytest's elapsed-time footer as a
  false digest mismatch. FIX: support explicit, reviewed output-normalization
  rules in challenge definitions instead of embedding the S11 wrapper.
- Add a subprocess-spawn test seam or bounded fake runner for score-time tests.
  WHY: full S11 proof takes roughly a minute per challenge/re-check. FIX: keep
  one real dogfood test and inject a deterministic executor for unit coverage.
- Document runner-key lifecycle and rotation. WHY: deleting or replacing the
  0600 key intentionally invalidates stored receipts, but that operator effect
  is currently implicit. FIX: add a short rotate/revoke procedure and receipt
  invalidation note.
