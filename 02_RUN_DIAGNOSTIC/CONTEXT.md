# Diagnostic Stage Context

Use this stage for the full read-only CheckYourself diagnostic.

## Inputs

| Input | Required? | Notes |
|---|---|---|
| Project files, repo, export, screenshots, or description | Yes | Ask for the smallest missing context if blocked. |
| App profile and unknowns | Preferred | From `01_PROJECT_CONTEXT/`. |
| User risk tolerance | Optional | Do not let it hide P0/P1 findings. |

## Process

1. Read `rules.md`, `coverage-matrix.md`, and `scoring-method.md`.
2. Get deterministic receipts first when Python 3 is available:
   `python3 tools/checkyourself.py scan <project> --format json --no-write`
   for stack signals and deterministic findings, then
   `python3 tools/checkyourself.py coverage --emit` for the coverage skeleton,
   and after filling it with evidence,
   `python3 tools/checkyourself.py score --findings <scan.json> --coverage <coverage.json>`.
   Treat scanner findings as confirmed evidence. Do not invent a separate
   scoring or backlog path. If Python is unavailable, run the same sweep
   manually and say the score is hand-computed using `scoring-method.md`.
3. Inspect evidence before assumptions.
4. Represent every coverage-matrix row as Pass, Finding, Unknown, or N/A.
5. Rank findings by harm and reversibility using `risk-taxonomy.md`.
6. Produce the Production Reality Report using
   `05_OUTPUT_TEMPLATES/production-reality-report.md`.
7. Select the safest first approval batch from the complete backlog.
8. On a recheck, compare the new scan against the prior baseline with
   `python3 tools/checkyourself.py diff --old <baseline.json> --new <current.json> --ci`
   to confirm risk went down and no P0/P1 regressed.
9. Offer guided fix mode, dashboard mode, and learning plan only after the
   report exists.

## Outputs

| Output | Where |
|---|---|
| Production Reality Report | Chat by default, or `02_RUN_DIAGNOSTIC/output/production-reality-report.md` if file output is requested |
| Evidence summary | Included in the report |
| First approval batch | Included in the report |

## Handoff

- Send approved remediation work to `03_GUIDED_FIX_MODE/CONTEXT.md`.
- Send learning-plan work to `04_LEARNING_PLAN/CONTEXT.md`.
- Send dashboard requests to `10_DASHBOARD/CONTEXT.md`.

## Do Not

- Do not change files during diagnostic mode.
- Do not generate an HTML dashboard unless the user asks for it.
- Do not stop after the first few obvious issues.
