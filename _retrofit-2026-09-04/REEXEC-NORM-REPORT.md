# Re-execution normalization report

## Outcome

Semantic re-execution equality is implemented for executed challenge receipts.
Fresh runs no longer need byte-for-byte output equality when only volatile
runtime values changed. Raw capture hashing remains in place as tamper evidence
for the stored capture.

## Implementation

- Added the documented deterministic normalizer in `tools/checkyourself.py`.
  It removes carriage returns, strips trailing line whitespace, and replaces
  `in <number>s|ms` durations, `H:MM:SS` durations, ISO-8601 timestamps, and
  absolute project/temp paths with placeholders.
- Added `semantic_output_digest`, a SHA-256 over canonical JSON containing
  exit code, normalized stdout/stderr, and command argv.
- Challenge receipts now store and bind `semantic_output_digest` in both the
  receipt hash and local HMAC.
- Score-time verification checks exit code, fresh assertions, and semantic
  digest. It no longer compares fresh raw capture bytes to the stored raw
  capture digest.
- Receipts without the semantic field use the legacy binding for verification
  and re-derive the semantic digest from the stored capture.
- Raised the repository S11 timeout from 120s to 180s after the exact captured
  suite command measured 137.45s; the final direct suite run took 89.49s.

## Regression coverage

| Case | Result |
|---|---|
| Duration-varying output, scored twice | Executed credit retained; C5 Pass both times |
| Content edit in fresh output | Unknown via semantic digest mismatch |
| Exit-code drift | Unknown via exit-code mismatch |
| Fresh assertion failure | Unknown via fresh assertion failure |
| Legacy receipt without semantic field | Re-derived and accepted |
| Stored capture edit | Raw capture digest still rejects tampering |

## Verification receipts

- `python3 -m pytest tests/ -q`: **150 passed, 88 subtests passed**.
- `python3 tools/validate_public.py .`: **passed**.
- `python3 tools/checkyourself.py validate --kind challenges .checkyourself/challenges.json --format json`: schema and semantic validation **passed**.
- Final S11 challenge: **PASS**, complete, no findings, semantic digest present.
- Final S11 score round-trip: two independent score invocations exited 0;
  both returned `C5=Pass`, score `34`, confidence `low`. The overall score is
  intentionally low because the ad hoc coverage artifact supplied only S11;
  this proves the S11 receipt path, not whole-project readiness.

No commit or push was made.

## IMPROVEMENTS

1. Add a small standalone fixture command for S11 dogfood so receipt round-trip
   checks do not require the full 150-test suite on every local verification;
   the full suite should remain the release gate.
2. Keep a measured runtime budget beside each committed challenge; the first
   live attempt timed out at 120s even though the suite was healthy, which hid
   the semantic verifier behind an operational timeout.
