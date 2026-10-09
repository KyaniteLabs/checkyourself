# Retrofit Process Learnings — 2026-09-04

This note records process lessons from the documentation, validation, and
evidence close-out. It is for maintainers running future multi-worker changes;
it does not change the product contract.

## Evidence freshness has two clocks

A worker can observe a correct local projection while the orchestrator's branch
still lacks that projection. The reverse also happens: a commit can exist while
generated receipts, screenshots, or reports still describe an older tree. A
"code-complete" report is therefore not proof that the committed or released
surface is current.

Keep these states separate in every wave:

1. worker worktree state;
2. orchestrator branch state;
3. default-branch or release state;
4. generated proof state.

Record the source state used for each receipt, regenerate derived proof from one
captured evidence set, and re-run acceptance after integration. Treat a report
that projects a future commit as a plan, not as current proof.

## Public validation needs an artifact boundary

Retrofit reports are process evidence, not public product documentation. When a
public Markdown/link validator walks `_retrofit-*` artifacts, intentionally
incomplete evidence links can make the public gate fail and hide whether the
product surface itself is healthy. This is a boundary-design failure, not a
reason to erase useful evidence.

Choose one explicit policy before the next retrofit: exclude process-artifact
directories from public validation, or validate them with a separate historical
artifact contract. Keep the exclusion narrow and visible, and report both
product-surface results and artifact-contract results separately.

## License files and badges are different evidence classes

A README badge is a presentation claim. The LICENSE file is the legal artifact;
the manifest and NOTICE provide machine-readable and attribution context. A
green badge cannot override a conflicting license file. Resolve the owner's
legal choice first, then align the badge, prose, manifest, LICENSE, and NOTICE
as one change and validate every public claim.

## Capture the baseline before changing a wave

The required validator and full test suite repeatedly exposed inherited README
and retrofit-artifact failures only after a worker had changed code. Without a
pre-wave receipt, an acceptance failure is ambiguous: regression, inherited
debt, or an artifact owned by another lane.

Before implementation, capture the exact commands, exit codes, failure list,
and ownership of known failures. After implementation, compare the same checks
with the same scope. A wave passes only when it introduces no new failure; an
inherited failure remains visible and explicitly out of scope.

## Orchestrator and worker Git ownership must stay explicit

Workers need a precise changed-file list and verification receipt, but the
orchestrator owns branch integration and commits. A worker's local clean status
or commit is not a merged delivery receipt, and an orchestrator's integration
commit does not replace worker-level proof.

The dispatch brief should name the owner of branch, commit, push, and release
actions. The worker report should list every changed file and the exact checks
run. The orchestrator should re-check the integrated tree before reporting
completion. Keep task-tracker setup in the worker harness ready before dispatch;
otherwise even status bookkeeping becomes an avoidable failure mode.

## Generated receipts should have one reproducible producer

Manual date and scan-count edits created avoidable freshness drift during the
close-out. A dependency-free receipt command should capture scan, coverage,
score, and rendering inputs once, then generate all derived proof from that
same evidence. Until such a command exists, label hand-refreshed receipts with
their source date, scope, and known proof gaps.

## Retrofit completion: verifier authority has a boundary

The retrofit added a verifier-owned `challenge` path, score-time
re-execution, semantic vacuity contracts, local integrity binding, claim
binding, and semantic report validation. The useful lesson is to name each
authority boundary explicitly: a committed challenge definition can constrain
what the verifier runs, an executed receipt can preserve observed output, and
semantic validation can recompute a verdict. None of these facts makes the
score a production-safety guarantee or gives a project-local HMAC independent
issuance authority.

The final proof at `cd9cf85` recorded 150 tests and 88 subtests passed, public
validation passed, and the matrix contained 20 canonical surfaces across 10
scored categories. Keep those counts attached to their command and source
revision; do not turn them into timeless product claims.

## Retrofit completion: documentation must mirror the executable contract

README and `llms.txt` now repeat the same capability facts and limits: argv-only
challenge commands, bounded timeouts, fail-closed failures, `EXECUTED` as the
only full-credit receipt class, caller-issued receipts as capped `UNVERIFIED`,
semantic output normalization, per-surface anti-vacuity contracts, local HMAC
tamper evidence, `--claim` bindings, and separate schema versus semantic report
validation. The public validator checks repository shape and links; a second
fact-agreement probe is still useful because prose drift can remain valid
Markdown.
