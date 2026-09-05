# FINAL Grok independent review (HEAD cd9cf85)

HEAD: `cd9cf853a3cd1b13ac213df25eb4fbb4142372db` (`retrofit/2026-09-04`)
Method: read-only; pytest; `validate_public.py`; in-memory temp trees only. No repo writes besides this report, no network, no git ops.

## Acceptance chain

- `python3 -m pytest tests/ -q` → **150 passed, 88 subtests passed** (94.40s)
- `python3 tools/validate_public.py .` → **OK: public CheckYourself validation passed**
- `python3 tools/checkyourself.py validate --kind challenges .checkyourself/challenges.json --format json` → `valid: true`, schema + semantic

## Probe results (in-memory, fail-closed required)

| Probe | Result | Verdict |
| --- | --- | --- |
| CONTROL genuine S11 (`import pytest; print('1 passed in 0.01s')`) | C5 Pass, awarded 10 | expected credit |
| E1 drop `local_integrity_hmac` | C5 not Pass; confidence not high | fail closed |
| E1 HMAC = `0*64` | C5 not Pass | fail closed |
| Steal project key, edit capture, rehash semantic digest, resign | C5 not Pass (re-exec semantic mismatch) | fail closed |
| HMAC replay onto other `run_id` | C5 not Pass | fail closed |
| VACUITY `true` | challenge FAIL + vacuous reasons; no Pass credit | fail closed |
| VACUITY `echo` | challenge FAIL; no Pass credit | fail closed |
| VACUITY `regex_match: .*` | challenge FAIL; no Pass credit | fail closed |
| HOLLOW `python -c pass` | challenge FAIL; no Pass credit | fail closed |
| CROSS-SURFACE S11 receipt scored as S01 | C1 not Pass | fail closed |
| CROSS-SURFACE S01 configured as pytest-shaped command | not Pass / FAIL | fail closed |
| OVERRIDE `.checkyourself.json` cannot displace `challenges.json` | command stayed committed argv | fail closed |
| OVERRIDE-only `true` in `.checkyourself.json` | FAIL + no Pass credit | fail closed |
| NORM: duration/timestamp collapse keeps extra tokens | P0 / FINDING / CLEAN remain distinct | fail closed |
| NORM ABUSE: extra `CY-SECRET-001` after duration, steal-key resign | C5 not Pass (re-exec digest) | fail closed |

## False-green hunt

Hostile EXECUTED JSON does not earn executed credit without a matching per-run local HMAC **and** live semantic re-execution. Vacuous commands and trivial regexes are rejected before credit. Coverage cannot reuse a receipt across surfaces. Dedicated `challenges.json` wins over a sibling override file.

Residual (honest, not a probe miss): HMAC is **project-local tamper evidence** (`.checkyourself/local-integrity-binding.key`), not independent attestation. S11 still accepts a command that *mentions* a test runner and prints a pass-count (the shipped fixture). That is marker-based substance, not a real runner adapter.

## Verdict

Required probe classes fail closed on HEAD `cd9cf85`. Acceptance chain is green.

FULLY-GREEN: yes

## IMPROVEMENTS

1. Replace S11 runner *markers* with adapters that parse native result schema. WHY: `import pytest; print('1 passed')` is still EXECUTED credit. FIX: require a real runner invocation or structured pytest JSON report.
2. Bind artifact bytes into executed receipts. WHY: artifact-surface contracts check non-empty path at run time but do not re-hash the artifact on replay. FIX: store path+digest and re-check at score.
3. Keep a tiny S11 dogfood command beside the 150-test suite. WHY: full-suite timeouts previously hid the semantic verifier. FIX: fixture challenge for receipt round-trip; keep full suite as the release gate.
