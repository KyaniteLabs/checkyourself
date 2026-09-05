# STREAK 10 — Grok independent review (post runner-harden a5ec5ae)

HEAD: `a5ec5aecb933c5b07b60c08fafd7c720012528b5` (`retrofit/2026-09-04`)
Method: read-only; pytest; `validate_public.py`; in-memory temp trees only. No repo writes, no network, no git ops.

## Acceptance chain

- `python3 -m pytest tests/ -q` → **139 passed, 88 subtests passed**
- `python3 tools/validate_public.py .` → **OK: public CheckYourself validation passed**

## Probe results (in-memory)

| Probe | Result | C5 / notes | Verdict |
| --- | --- | --- | --- |
| E1 — forged EXECUTED, merged digest, drop `receipt_hmac` | Unknown + caps 84+90 | HMAC missing | fail closed |
| E1-zero — HMAC = `0*64` | Unknown | HMAC invalid | fail closed |
| HMAC replay — copy run1 HMAC onto run2 (different `run_id`) | Unknown | HMAC mismatch | fail closed |
| HMAC replay — copy `run_id`+HMAC, mutate `timestamp`, rehash sha256 | Unknown | `runner HMAC does not cover executed fields` | fail closed |
| Capture-edit-then-rehash — edit capture, recompute digest, resign with stolen key | Unknown | `re-executed output digest does not match the receipt` | fail closed |
| Re-exec substitution — swap `challenges.json` after issue | Unknown | config digest / command mismatch | fail closed |
| Re-exec substitution — steal key, set new digest, keep old command | Unknown | command ≠ committed definition | fail closed |
| Re-exec substitution — steal key, swap command+digest to new config | Unknown | live re-exec digest ≠ stored capture | fail closed |
| Keyfile theft — steal 0600 key, sign forged capture | Unknown | re-exec digest mismatch | fail closed |
| Control — genuine signed receipt, unchanged tree | C5 Pass | expected | not an escape |

Same-second footnote: two genuine runs in one UTC second share timestamp and overwrite the same `S11.capture.json`. Copying `run_id`+HMAC from run1 onto run2 **without** mutating other binding fields can verify as Pass. That is a clone of run1’s binding, not a new execution proof. Mutating any bound field (timestamp) fails HMAC.

## Findings

1. **E1 class is closed.** Shape-correct EXECUTED JSON without a valid per-run HMAC does not score executed credit.
2. **HMAC is run-bound.** Replay onto a different `run_id` or mutated binding fails before re-exec.
3. **Re-execution is the second gate.** Stolen key + edited capture + rehashed HMAC still fails when the live argv output does not match the stored digest. Swapping challenge config between issue and score also fails closed.
4. **Residual (by design, not E1):** possession of `.checkyourself/challenge-runner.key` plus the ability to run the committed command is equivalent to being the runner. Key mode 0600 is the remaining trust boundary; there is no remote attestation.

## False-green hunt

Shipped tests cover E1-without-HMAC, invalid HMAC, capture edit (without rehash), and excluded-state re-exec mismatch. They do **not** cover HMAC cross-run replay or capture-edit-then-resign. Live probes of those paths still fail closed.

FULLY-GREEN: yes
