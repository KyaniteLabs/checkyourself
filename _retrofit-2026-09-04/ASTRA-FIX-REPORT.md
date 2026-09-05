# ASTRA Wave Fix Report

Date: 2026-09-05
Scope: all eight findings in `ASTRA-REVIEW.md`
Git: no commit or push performed

## Finding status

| # | Severity | Status | Evidence | Regression / acceptance proof |
|---:|---|---|---|---|
| 1 | SEV-1 | CLOSED | `tools/checkyourself.py:1526-1614` verifies in-root, non-empty artifacts, SHA-256, provenance, and binding to reviewer references. `coverage_check` marks unresolved receipts incomplete with warnings. | `tests/test_checkyourself_cli.py:1954` proves fabricated references cannot earn Pass/high credit; direct adversarial score: 29/100, low confidence. |
| 2 | SEV-1 | CLOSED | `tools/checkyourself.py:1601-1611` requires a verifier-captured `delegation_receipts` artifact for `NotApplicable`; `schemas/coverage.schema.json` defines the receipt contract. | `tests/test_checkyourself_cli.py:768` proves blanket N/A is Unknown, capped, and low confidence. `tests/test_checkyourself_cli.py:728` proves a real delegation receipt preserves the category weight. |
| 3 | SEV-1 | CLOSED | `tools/checkyourself.py:204-205` separates workflow dispositions from residual-risk closure; only `fixed` and verified `not-applicable` are resolved for scoring. `score` emits `workflow_dispositions`. | `tests/test_checkyourself_cli.py:1972` proves an accepted P0 remains counted, penalized, capped at 49, and reports `residual_risk: open`. |
| 4 | SEV-1 | CLOSED | `tools/checkyourself.py:1885-2010` tracks `has_unknown` independently of category status and synthesizes a coverage-finding penalty when an unlinked coverage row is `Finding`. | `tests/test_checkyourself_cli.py:1992` proves S06 Unknown remains a critical evidence gap when S07 is Finding; score is low and capped. |
| 5 | SEV-2 | CLOSED | `samples/sample-production-reality-report.md:7-13` labels Observed/Inferred/Untested claims; `:31-37` makes the decisive authorization check precede any code prescription. `05_OUTPUT_TEMPLATES/production-reality-report.md:26-42` adds the reusable claim/proof boundary. | Sample no longer presents an unsupported Medium-confidence score or unconditional ownership-check fix. |
| 6 | SEV-2 | CLOSED | `tools/checkyourself.py:2828-2910` returns separate schema and semantic validity and recomputes caps, confidence, coverage completeness, findings/backlog reconciliation, and full score breakdowns. | `tests/test_checkyourself_cli.py:1766` proves a schema-valid golden report with an open P0 cannot validate as a 100/high verdict. |
| 7 | SEV-2 | CLOSED | `README.md:1-3,39-43,257-272`, `skills/checkyourself/SKILL.md:3,10`, and `llms.txt:3` position the product around reviewable completion evidence, bounded scoring, local receipts, and explicit verification limits. | Public validator passes; discovery copy no longer presents the score as a production-safety guarantee. |
| 8 | SEV-2 | CLOSED FOR THIS WAVE | `tools/checkyourself.py:2233-2250,3709` adds `--claim`, records the accepted completion claim, and emits explicit claim-bound/unbound evidence rows. No challenge runner was added. | `tests/test_checkyourself_cli.py:1794` proves the claim and binding fields. The independent verifier-owned challenge runner remains explicitly deferred to the next cycle. |

## Acceptance receipts

- `python3 -m pytest tests/ -q` — **120 passed, 86 subtests passed**.
- `python3 tools/validate_public.py .` — **OK: public CheckYourself validation passed**.
- `python3 -m py_compile tools/checkyourself.py tools/validate_public.py` — passed.
- `git diff --check` — passed.
- Golden report tamper case — schema-valid input is rejected by semantic validation with the unresolved P0 cap error.
- S06/S07 case — an S06 Unknown remains visible and confidence remains low when S07 is Finding.
- Existing tests were not deleted. The prior fake-receipt high-confidence fixture was changed to create real temporary receipts; the prior reason-only N/A fixture now uses a real delegation receipt, and a separate regression test preserves the rejected reason-only behavior.

## Remaining boundary

`--claim` records the accepted completion claim and explicit evidence binding, but it does not independently execute or invalidate a challenge receipt. That is intentionally the next-cycle design boundary identified by ASTRA #8.

## IMPROVEMENTS

1. Add the verifier-owned challenge runner next cycle; the current `--claim` boundary records binding but cannot establish behavior independently.
2. Add a single receipt-generation command; the wave currently requires callers to produce artifact hashes and provenance fields themselves.
3. Add claim-aware report generation; the current CLI records claims in score artifacts while human report assembly remains template-driven.
