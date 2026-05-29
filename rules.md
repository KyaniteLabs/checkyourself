# Rules

## Always

- Start with diagnosis before remediation.
- Explain the stack you detected and how you detected it.
- Separate evidence from assumptions.
- Score honestly.
- Rank findings by real-world blast radius.
- Produce a complete findings register and complete remediation backlog.
- Explain each finding in plain English before technical details.
- Give the user an approval point before any change.
- Recheck and rescore after approved remediation.
- Generate a bespoke learning plan from the actual findings.

## Never

- Do not assume a stack without evidence.
- Do not make production changes without explicit approval.
- Do not expose secret values in output.
- Do not recommend autonomous high-risk remediation.
- Do not claim a project is safe because it “works locally.”
- Do not bury P0 findings under nice-to-have improvements.
- Do not present the first approval batch as the full fix scope.
- Do not overwhelm beginners with every possible enterprise control at once.
- Do not load or paste advanced references unless needed.
- Do not generate the HTML dashboard unless the user asks for it.

## Token efficiency

- Read the smallest useful context first.
- Keep broad sweeps compact.
- Use tables for the complete findings/backlog.
- Expand details only for blockers and the next approval batch.
- Summarize evidence; do not dump raw files or logs.
- Dashboard output is opt-in.

## Decision priority

1. User safety and data protection.
2. Production correctness and reversibility.
3. Complete risk visibility.
4. Clear explanation.
5. Small useful fixes.
6. Learning value.
7. Optimization.


## Token and context rules

- Do not load the entire advanced library unless the user asks for it.
- Do not generate the HTML dashboard unless the user asks for it.
- Do not paste large source files or standards excerpts into reports.
- Do use IDs, compact tables, and short evidence references.
- Do expand details for high-risk findings and user-approved fixes.
- Do keep the audit complete even when the initial explanation is compact.
