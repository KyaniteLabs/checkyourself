# Diagnostic Stage Context

Read-only diagnostic stage.

## Inputs

Project files, repo, export, screenshots, or description are required; ask for
the smallest missing context. App profile/unknowns from `01_PROJECT_CONTEXT/`
are preferred. Risk tolerance is optional and cannot hide P0/P1 findings.

## Process

1. Read `rules.md`, `coverage-matrix.md`, and `scoring-method.md`.
2. With Python 3, get receipts:
   `python3 tools/checkyourself.py scan <project> --format json --no-write`,
   `python3 tools/checkyourself.py coverage --emit`, fill evidence, then run
   `python3 tools/checkyourself.py score --findings <scan.json> --coverage <coverage.json>`.
   Treat findings as evidence; do not invent another scoring/backlog path. If
   Python is unavailable, sweep manually and label the score hand-computed.
3. Inspect before assuming; mark each row Pass, Finding, Unknown, or Not applicable.
4. Rank by harm/reversibility with `risk-taxonomy.md`.
5. Write `05_OUTPUT_TEMPLATES/production-reality-report.md` and choose the
   safest first batch from the complete backlog.
6. On recheck, compare with
   `python3 tools/checkyourself.py diff --old <baseline.json> --new <current.json> --ci`.
7. Offer guided fixes, dashboard mode, and learning only after the report.

## Outputs / handoff

- Report: chat by default, or `02_RUN_DIAGNOSTIC/output/production-reality-report.md` when requested.
- Evidence summary and first approval batch: in the report.
- Fixes: `03_GUIDED_FIX_MODE/CONTEXT.md`; learning:
  `04_LEARNING_PLAN/CONTEXT.md`; dashboards: `10_DASHBOARD/CONTEXT.md`.

## Do not

Change files during diagnostic mode; generate HTML unless requested; or stop
after the first obvious issues.
