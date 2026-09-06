# DOCS2 Report — Public Documentation Retrofit

Date: 2026-09-05
Scope: README.md, llms.txt, CHANGELOG.md, docs/RETROFIT-LEARNINGS-2026-09-04.md
Git: no commit or push performed

## Fact table

| Claim | Evidence | Verification |
|---|---|---|
| The verifier executes the `challenge` verb from committed `.checkyourself/challenges.json`; commands are argv-only, time-bounded, and FAIL is fail-closed. | `tools/checkyourself.py` challenge loading/execution; `.checkyourself/challenges.json`; `_retrofit-2026-09-04/CHALLENGE-RUNNER-REPORT.md` | Public validator passed; challenge schema and semantic validation are part of the repository contract. |
| Successful verifier-executed `EXECUTED` receipts are the only full-credit class; caller-issued receipts are capped `UNVERIFIED`. | `tools/checkyourself.py` receipt/scoring paths; `CHALLENGE-RUNNER-REPORT.md` | Regression evidence is recorded in the challenge-runner report. |
| Score-time re-execution checks exit state, assertions, source/challenge binding, and semantic output digest with volatile-token normalization. | `tools/checkyourself.py` re-execution paths; `REEXEC-NORM-REPORT.md`; `RUNNER-HARDEN-REPORT.md` | `python3 -m pytest tests/ -q` passed: 150 tests, 88 subtests. |
| Semantic vacuity is rejected or capped through verifier-owned per-surface minimum contracts. | `tools/checkyourself.py` semantic challenge contracts; `VACUITY-REPORT.md` | No-op, echo, print-only, hollow-runner, and trivial-regex probes are recorded as fail-closed. |
| Local HMAC binding is project-local tamper evidence, not independent issuance or operator identity; external custody is future work. | `RUNNER-HARDEN-REPORT.md`; `VACUITY-REPORT.md`; `FINAL-sol.md` | README and llms.txt state the boundary explicitly. |
| `--claim` records the accepted completion claim and distinguishes claim-bound from unbound evidence. | `tools/checkyourself.py` claim path; `ASTRA-FIX-REPORT.md` | README and llms.txt expose the binding boundary. |
| Report validation separates schema validity from semantic verdict consistency and recomputes verdicts. | `tools/checkyourself.py` report validation; `ASTRA-FIX-REPORT.md` | README and llms.txt state both validation classes. |
| ASTRA found eight findings and the retrofit closed them. | [`ASTRA-REVIEW.md`](ASTRA-REVIEW.md); [`ASTRA-FIX-REPORT.md`](ASTRA-FIX-REPORT.md) | Fix report marks all eight findings closed or closed for the wave. |
| The live matrix contains 20 canonical surfaces and 10 scored categories. | `tools/checkyourself.py:COVERAGE_SURFACES`; `tools/checkyourself.py:SCORE_CATEGORIES`; `CHALLENGE-RUNNER-REPORT.md` | `coverage --emit` returned 20 surfaces; the scorer defines 10 scored categories. |
| The current test receipt is 150 tests and 88 subtests. | `REEXEC-NORM-REPORT.md`; `FINAL-grok.md`; `FINAL-sol.md` | `python3 -m pytest tests/ -q` passed: 150 tests, 88 subtests. |
| The public validator passes and the license claim remains Apache-2.0. | `tools/validate_public.py`; `LICENSE`; `checkyourself.manifest.json`; README badge/footer | `python3 tools/validate_public.py .` returned `OK: public CheckYourself validation passed`. |
| README and llms.txt agree on the retrofit capabilities and limits. | `README.md`; `llms.txt` | Manual fact-agreement probe checked challenge, receipt, re-execution, vacuity, HMAC, claim, semantic validation, counts, and boundaries after editing. |

## Acceptance commands

```text
python3 -m pytest tests/ -q
150 passed, 88 subtests passed

python3 tools/validate_public.py .
OK: public CheckYourself validation passed
```

The docs update is complete for this wave. The score, local HMAC, test count,
and validator result remain scoped repository evidence; none is a production
readiness guarantee.

## IMPROVEMENTS

1. Add a small executable README/llms fact-agreement checker. WHY: the public
   validator checks links and shape but does not catch prose drift. FIX: define
   a compact fact manifest and compare both docs in CI.
2. Generate the test-count receipt from the challenge result. WHY: hand-copying
   `150` and `88` can go stale after the next test change. FIX: emit a dated,
   source-revision-bound summary artifact from the committed S11 challenge.
