# Guided Fix Stage Context

Use this stage only after a diagnostic exists and the user approves a specific
fix or batch.

## Inputs

| Input | Required? | Notes |
|---|---|---|
| Production Reality Report | Yes | Source of truth for findings and backlog. |
| User approval | Yes | Approval must name the fix or batch. |
| Project files | Yes | Apply the smallest reversible change. |
| Verification command or plan | Preferred | Use the best available proof. |

## Process

1. Restate the approved finding IDs and files likely touched.
2. Make only the approved minimal change.
3. Verify the affected behavior where possible.
4. Update finding status, score rationale, and learning notes.
5. Offer the next safest batch from the remaining backlog.

## Outputs

| Output | Where |
|---|---|
| Fix proposal | Chat before approval |
| Remediation log | `03_GUIDED_FIX_MODE/output/remediation-log.md` when file output is requested |
| Recheck report | `03_GUIDED_FIX_MODE/output/recheck-report.md` when file output is requested |

## Handoff

- Send updated learning needs to `04_LEARNING_PLAN/CONTEXT.md`.
- Send updated report/dashboard requests to `10_DASHBOARD/CONTEXT.md`.

## Do Not

- Do not broaden scope without approval.
- Do not mark findings fixed without verification evidence or an explicit
  limitation.
- Do not remove unresolved findings from the backlog.
