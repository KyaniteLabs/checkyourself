# Complete Prioritized Fix Plan

This plan should include every confirmed finding and every blocking unknown from the diagnostic. It is not limited to the first few fixes.

| Order | Severity | Finding ID | Finding | Fix | Files/systems | Verification | Rollback | Approved? | Status | Learning item |
|---:|---|---|---|---|---|---|---|---|---|---|
| 1 | P0 |  |  |  |  |  |  |  |  |  |

## First approval batch

The first approval batch is the safest starting point from the full plan. It is not the whole plan.

| Batch item | Finding ID | Why first | Approval question |
|---:|---|---|---|

## Continue-until-done loop

After each approved fix:

1. Make the smallest reversible change.
2. Verify the change.
3. Update the finding status.
4. Recalculate the score if the finding affected scoring.
5. Update the learning plan.
6. Ask for approval for the next backlog item or batch.

Default exit criteria:

- No unresolved P0 findings.
- No unresolved P1 findings before public launch.
- P2/P3 items are either fixed, explicitly accepted, or scheduled.
