# CheckYourself Field Postmortem: Real Repo Remediation Loop

Date: 2026-05-29

Context: CheckYourself was used as the operating system for a public GitHub repo hardening loop across KyaniteLabs projects, including Epoch, dev-learning-archaeologist, liminal-sites, and liminal.

## What Worked

- The severity language forced the right conversation. P0/P1/P2/P3 made it harder to hand-wave risk.
- The score caps prevented fake 100s while real launch blockers existed.
- The folder-first workflow helped agents stay oriented without needing a hosted service.
- The CLI/MCP split was right: CLI owns deterministic work; MCP stays a thin wrapper.
- The dashboard and reports were useful when they showed real data and fresh screenshots.

## Gaps Found

### False-Positive P0s Were Too Expensive

The scanner could turn field names like `feedbackToken` into P0 secret findings without enough credential-shape evidence. That wasted remediation energy on cosmetic renames instead of real risk.

Remediation:

- Add `.checkyourself.yml` suppressions.
- Keep suppressed findings visible in JSON.
- Require stronger evidence for P0 secret findings.
- Add line numbers, match type, confidence, and redacted context.

### Score Without Coverage Was Ambiguous

`score --findings scan.json` returned a number that looked official even when coverage evidence was missing. That invited arguments about whether the score was a deterministic estimate or a production-readiness score.

Remediation:

- Add `score_mode`.
- Treat no-coverage scoring as a low-confidence scan-derived estimate.
- Return `manual_evidence_needed`.
- Keep coverage-backed scoring as the real high-confidence path.

### There Was No Memory Of Improvement

The tool did not record baseline-to-final score movement. That made delivery proof depend on the agent's memory instead of a local receipt.

Remediation:

- Append score receipts to `.checkyourself-score-history.json` by default.
- Support `--history`, `--note`, and `--no-history`.

### The Word "Diagnostic" Existed In The Product But Not The CLI

Docs and agent workflows naturally said "run a diagnostic," but the CLI only had `scan`.

Remediation:

- Add `diagnostic` as an alias for `scan`.

### Single-Pass Scans Missed Follow-Up Validation

The scan detected CI and tests, but did not validate obvious second-order risks like mutable GitHub Action refs or missing dependency update automation.

Remediation:

- Add `scan --deep` for conservative, slower validation checks.
- Start with CI action pinning, dependency update coverage, and sensitive `.gitignore` patterns.

### CI Integration Was Manual

The scanner had to be run by an agent or human. Public repos need a PR gate.

Remediation:

- Add a composite GitHub Action that runs scan JSON, validates it, and fails on unresolved P0 findings when enabled.

## Bottlenecks

- Cross-repo audit output needs a dedicated runner/report format. Today the agent has to coordinate repo discovery, scan output, scoring, and prioritization manually.
- Deep checks need to grow carefully. The tool should validate detected surfaces without becoming noisy SAST cosplay.
- Coverage still requires human or agent judgment. That is correct, but the CLI must make the boundary unmistakable.
- Suppressions need social hygiene. A suppression without reason, reviewer, and date becomes risk laundering.

## Ambiguities

- A "100" can mean "no unresolved deterministic findings with coverage evidence" or "ready for launch." The docs now emphasize that score is evidence confidence, not permission to ship.
- `.env` presence can be local-only or a tracked disaster. CheckYourself can flag it, but git history still needs verification.
- A repo can be green locally while public GitHub still has stale branches, open alerts, or failed checks. Public remote state must be part of the final proof.

## Contradictions

- The product says diagnose before fixing, but real remediation loops need a way to carry reviewed exceptions forward. Suppressions resolve that tension without hiding the evidence.
- The CLI says deterministic, but scoring without coverage relied on missing-evidence caps that felt like judgment. `score_mode` now separates deterministic scan estimates from coverage-backed scoring.
- The docs framed CI use, but the repo had no action surface. The composite action closes that gap.

## Missed Opportunities

- CheckYourself should produce a cross-repo portfolio report: urgency ranking, score delta, open GitHub risks, and next repo queue.
- Learning priorities should be generated from actual recurring findings across repos, not one project at a time.
- The dashboard should have a "staleness" receipt so screenshots and HTML cannot quietly drift.
- The CLI should eventually emit a remediation ledger that can be appended after each PR merge.

## Product Rule Added

CheckYourself must never make the user fight the checker instead of the risk. If a finding is real, make it easy to fix. If it is benign, make it easy to prove, suppress, and keep moving with receipts.
