# 03 — Guided Fix Mode

Guided fix mode starts only after the diagnostic and only with user approval.

The goal is to remediate the complete backlog in safe, understandable, reversible steps. The first approval batch is just the starting sequence. It is not the whole scope.

## Remediation model

1. Start from the complete remediation backlog in the Production Reality Report.
2. Fix P0 items first unless the user explicitly accepts the risk.
3. Then fix P1 items before public launch.
4. Then work through P2/P3 items or schedule/accept them explicitly.
5. After each fix, re-check the affected area and update the score, backlog, and learning plan.

## Fix proposal format

Every fix proposal must include:

1. **Finding** — which diagnostic finding this addresses.
2. **Plain-English explanation** — why this matters.
3. **Technical explanation** — what is probably wrong.
4. **Minimal fix** — smallest safe change.
5. **Files likely touched** — expected scope.
6. **Verification** — tests/checks/manual steps.
7. **Rollback** — how to undo.
8. **Learning note** — what the user learns.
9. **Approval question** — ask before changing.

## Approval language

Use explicit approval prompts:

```text
Do you approve this specific fix or batch?
I will only touch the files listed above unless I discover a blocking issue, in which case I will stop and explain.
```

## After a fix

After remediation:

- summarize changed files;
- explain the diff in plain English;
- run or recommend verification;
- update the risk severity or mark the finding resolved;
- update the score if appropriate;
- add or update a learning-plan item;
- ask whether to continue to the next backlog item.

## Do not skip findings

If a finding is not fixed, it must be marked as one of:

- **Accepted risk** — the user knowingly accepts it.
- **Scheduled** — it has an owner or future step.
- **Blocked** — it needs missing access/context.
- **Not applicable after review** — the original finding was disproven.

## Completion policy

Guided fix mode is not a one-batch workflow.

After each approved batch:

1. apply the smallest safe change;
2. verify it;
3. update the finding status;
4. rescore;
5. offer the next safest batch.

Continue until every finding is one of:

- fixed;
- deferred with a reason and trigger;
- accepted as risk by the user;
- proven not applicable.
