# Density Pass Report

Date: 2026-09-05  
Scope: `skills/checkyourself/SKILL.md` plus non-README Markdown in
`02_RUN_DIAGNOSTIC`, `05_OUTPUT_TEMPLATES`, and `06_ADAPTERS`.

## Result

The combined scope clears the requested 20% body-token reduction.

| Scope | Before chars / 3.9 | After chars / 3.9 | Reduction |
|---|---:|---:|---:|
| `skills/checkyourself/SKILL.md` | 9,236 / 2,368.2 | 7,330 / 1,879.5 | 20.6% |
| `02_RUN_DIAGNOSTIC` | 13,110 / 3,361.5 | 10,379 / 2,661.3 | 20.8% |
| `05_OUTPUT_TEMPLATES` | 17,845 / 4,575.6 | 14,213 / 3,644.4 | 20.4% |
| `06_ADAPTERS` | 5,698 / 1,461.0 | 4,769 / 1,222.8 | 16.3% |
| **Combined** | **45,889 / 11,766.4** | **36,691 / 9,407.9** | **20.0%** |

`06_ADAPTERS` was already compact; the combined result is the acceptance
metric. No README, `llms.txt`, code, tests, schemas, or generated outputs were
changed.

## Method applied

- CAVEMAN: removed throat-clearing, hedges, duplicate framing, and long phrases.
- PONYTAIL: merged repeated dashboard policy, compacted tables, and made each
  line carry an instruction or output field.
- Protected code blocks remain byte-for-byte identical to `HEAD`.
- Protected commands, paths, IDs, status vocabulary, thresholds, provenance
  fields, and dashboard handoff paths remain represented.

## Losslessness review

Meaning-density check: no semantic exception identified. Rules and testable
claims survive in compressed form. Structural exceptions:

- `02_RUN_DIAGNOSTIC/diagnostic-prompt.md` stayed unchanged because its body is
  a protected verbatim prompt block.
- The report template keeps P0/P1/P2/P3 headings but uses one shared findings
  table with a `Severity` column; this removes repeated empty tables while
  retaining every finding field.
- `05_OUTPUT_TEMPLATES/risk-register.md`, `recheck-report.md`, and
  `approval-card.md` were already near-minimal; they were not forced below
  useful working-template density.

## Verification

- `python3 -m pytest tests/ -q` — **150 passed, 88 subtests passed**.
- `python3 tools/validate_public.py .` — **passed**.
- `git diff --check` — **passed**.
- Code-block comparison against `HEAD` — **all protected blocks identical**.
- Changed-file allowlist — **passed**; only the scoped docs changed.

## Gaps we noticed

- `td usage --new-session` could not create a session because this repository
  has no `td` database. This pass has no tracker receipt.
- Adapter density is lower than the other packs because provider setup steps
  and protected prompt blocks leave less compressible prose. Further cuts would
  trade away host-specific onboarding clarity.
- The template pack still has intentional duplication between dashboard
  guidance files. The pass reduced it without making each file depend on a
  reader loading another file; a future single-source template policy could
  reduce it further, but would be a separate structural change.

## IMPROVEMENTS

- Add a repository-local `td` database or an explicit docs-only exemption: the
  required session command failed before work tracking could start.
- Add a deterministic density-contract test for the scoped file list and the
  20% aggregate threshold: today the count is recorded manually in this report.
- Add a protected-literal validator for commands and paths, not only code
  blocks: the current proof compares fenced blocks and relies on the public
  validator for the rest.
