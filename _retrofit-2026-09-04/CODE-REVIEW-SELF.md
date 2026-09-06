# CheckYourself Code Review — Self-Dogfood

Date: 2026-09-05
Reviewed revision: `636e475`-equivalent live `main` tree; challenge tree digest `2daf5786c3c0fee8cb695626c58a113622b265e8445586a16cd217d17d9c3a33`
Scope: `tools/checkyourself.py`, `tests/`, `skills/checkyourself/SKILL.md`, `schemas/`, and the executable scan/coverage/challenge/score workflow.

## Result

Three P1 findings. The ordinary suite is green, but the challenge workflow's trust boundary and artifact contract are not: it can accept out-of-root evidence through a symlinked parent, timeout does not stop descendant processes, and its coverage schema rejects its executed receipts.

The deterministic scan inspected 281 files without truncation or unreadable/skipped files and reported zero detector findings. Manual adversarial review found the three defects below, which demonstrates the gap between pattern scanning and code review.

## Findings

| ID | Severity | Finding | Evidence | Impact |
|---|---|---|---|---|
| `CY-REVIEW-001` | P1 | Artifact assertions follow symlinked parent directories outside the project. | `tools/checkyourself.py:1149-1161`; reproduction with `root/linked -> external` and `artifact=linked/proof.txt` returned `('PASS', [])`. | A PASS receipt can certify evidence outside the reviewed project. |
| `CY-REVIEW-002` | P1 | A timed-out challenge leaves descendant processes alive. | `tools/checkyourself.py:1316-1368`; reproduction returned `timed_out=True` and `grandchild_alive_after_timeout=True`. | A reported timeout can leave code running, consuming resources or continuing mutations with inherited environment access. |
| `CY-REVIEW-003` | P1 | The coverage schema rejects executed challenge receipts. | `schemas/coverage.schema.json:38-56`, `tools/checkyourself.py:2689-2800`; `validate --kind coverage` rejected S11/S12/S13 executed receipts as the wrong shape. | The documented challenge-to-coverage-to-score artifact cannot be both evidence-bearing and schema-valid. |

No P0, P2, or P3 findings were confirmed in this bounded review.

## Verification

- `python3 -m pytest tests/ -q`: **PASS**, 150 tests and 88 subtests in 77.69s.
- `scan --deep`: **PASS as a scan execution**, 281 files, zero detector findings, complete scan limits.
- S11 challenge: **PASS standalone**.
- S12 challenge: **PASS standalone**, public validation passed.
- S13 challenge: **PASS standalone**, release tooling compiled.
- Coverage matrix: 20/20 canonical rows authored; 2 Pass, 2 Finding, 16 Unknown.
- Coverage schema validation: **FAIL** because the schema only accepts the caller-issued receipt shape and rejects all three executed receipts.
- Coverage receipt check: **incomplete**. Aggregate verification re-execution rejected S11 and S12 because their fresh exit codes did not match the stored receipts, even though both standalone challenges passed. This is reported as a proof gap, not waved through.

## Executed Receipt IDs

| Surface | Standalone status | Receipt SHA-256 |
|---|---|---|
| S11 Tests and quality | PASS | `2432a6bf5419cab6dd907014eac8bed4f61ad9e7ae6cb3ccba948b45a1fe484d` |
| S12 CI/CD and supply chain | PASS | `5e5c29a5f0737a377e0b6e7206590ac465e3e6fd5e10a53c3cdc8acb4d2a03ea` |
| S13 Release and rollback | PASS | `e3dfc7b3b16fec06c25aff6ae311fc4f44409c9d3e03b5b957da6d23f8297b4e` |

## Score Output

- Score: **19/100**
- Raw score: **19**
- Mode: `coverage-backed`
- Confidence: **low**
- Findings scored: `CY-REVIEW-001`, `CY-REVIEW-002`, `CY-REVIEW-003`
- Cap: 74 for three unresolved P1 findings; missing critical and launch-gate evidence also applied 84/90 caps but did not lower the 19-point raw score.
- Coverage complete: **false**, because most surfaces lack verifier-owned receipts and S11/S12 receipt re-execution did not agree in aggregate.

The low score describes evidence completeness for this review, not a claim that 81% of the CLI is broken.

## Artifacts

- `CODE-REVIEW-SELF.scan.json`: deterministic deep scan.
- `CODE-REVIEW-SELF.findings.json`: manual findings supplied to scoring.
- `coverage.json` at repository root: all 20 canonical coverage rows and embedded executed receipts.
- `CODE-REVIEW-SELF.coverage-check.json`: honest completeness result.
- `CODE-REVIEW-SELF.score.json`: executable score result.
- `CODE-REVIEW-SELF.challenge-S11.json`, `S12.json`, `S13.json`: standalone challenge outputs.

## What CheckYourself Cannot Catch Yet

1. **Filesystem-boundary semantics.** The scanner does not adversarially exercise symlinked parent paths in artifact assertions. Next cycle: add a path-containment invariant helper and hostile symlink fixtures for every evidence/output path.
2. **Process-tree containment.** The tests cover direct timeout state but not surviving descendants. Next cycle: add process-group termination and a child-survival regression test.
3. **Receipt schema, composability, and diagnostics.** The coverage schema rejects the runner's executed receipt shape; separately, standalone S11/S12 receipts passed while aggregate verification only reported an exit-code mismatch and discarded fresh stdout/stderr. Next cycle: define one compatible receipt union, preserve bounded re-execution diagnostics, and add an end-to-end mint → coverage validation → score test.
4. **Resource ceilings.** `capture_output=True` has no output-size bound. Next cycle: stream into bounded files, record truncation explicitly, and fail closed when semantic assertions depend on truncated output.
5. **Inherited execution environment.** Challenge subprocesses inherit the full parent environment. Next cycle: document the trust model and provide an allowlisted/minimal environment mode for untrusted repository review.

## Smallest Safe Fix Order

1. Fix artifact path containment and add the symlink-parent regression test.
2. Kill the entire challenge process group on timeout and prove descendants terminate.
3. Make the executed-receipt schema and multi-receipt coverage round trip compatible, deterministic, and diagnostic.

No repository code was changed. No git operations, installs, or network access were used.

## IMPROVEMENTS

1. **Improve timeout containment.** Why: the live reproduction left a child running after timeout. Fix: start a new process session, terminate its process group, then bounded-kill and test the full tree.
2. **Improve evidence-path validation.** Why: lexical containment accepted an external artifact through a symlinked parent. Fix: resolve strictly, reject symlink components, and require the resolved target under the resolved root.
3. **Improve dogfood receipt composition.** Why: independently passing receipts failed when checked together with only an exit-code mismatch. Fix: add a single end-to-end fixture for challenge → coverage → score and retain bounded fresh-output diagnostics on mismatch.
