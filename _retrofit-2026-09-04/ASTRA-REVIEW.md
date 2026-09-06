
## 1. The self-grading paradox

### #1 — SEV-1: Invent evidence-shaped receipts

**Lazy-agent strategy:** Fill every coverage row with `Pass`, cite `invented-receipts/check.txt:1`, and supply an empty findings list.

**Observed result:** `coverage_check` returned complete with zero warnings; scoring returned **100, high confidence, no caps**.

**Existing defense:** Empty Pass evidence becomes Unknown, and omitted scored surfaces become Unknown. The defense stops missing entries. Supplied evidence is accepted as strings; the additional coverage check looks for a filename-like pattern without opening the referenced artifact. [tools/checkyourself.py:1788](../tools/checkyourself.py), [tools/checkyourself.py:1801](../tools/checkyourself.py), [tools/checkyourself.py:1597](../tools/checkyourself.py)

This matches the existing successful-score fixture: repeated assertions that surfaces were verified in `src/app.py:10` earn 100/high without creating or inspecting that source. This is a trust assumption encoded in the contract. [tests/test_checkyourself_cli.py:1822](../tests/test_checkyourself_cli.py)

**Fix direction:** Separate reviewer assertions from verifier-captured evidence, and reserve verified credit for receipts whose origin, source state, and claimed result are checked.

### #2 — SEV-1: Outsource the entire denominator

**Lazy-agent strategy:** Mark every surface `NotApplicable` with “Handled by the upstream platform; outside this repository scope,” then supply no findings.

**Observed result:** **100/high**, complete coverage, zero warnings, zero evidence requests.

**Existing defense:** A missing applicability reason becomes Unknown; the written rubric requires genuine non-applicability. But the executable check accepts a nonempty reason, and the scoring contract deliberately awards full category weight. [02_RUN_DIAGNOSTIC/coverage-matrix.md:8](../02_RUN_DIAGNOSTIC/coverage-matrix.md), [tools/checkyourself.py:1792](../tools/checkyourself.py), [02_RUN_DIAGNOSTIC/scoring-method.md:22](../02_RUN_DIAGNOSTIC/scoring-method.md)

The conceptual hole is that **delegating a control does not establish its irrelevance**. An agent can replace an investigation into the provider’s responsibilities with a scope declaration.

**Fix direction:** Establish applicability independently of the grading agent and distinguish absent capabilities from delegated controls that still require evidence.

### #3 — SEV-1: Close the ticket, retain the vulnerability

**Lazy-agent strategy:** Preserve a known P0 cross-user access finding and its `Finding` coverage row, but change its status from `open` to `deferred` or `accepted-risk`.

**Observed result:** **49 → 100**, with high confidence throughout; the P0 cap disappeared.

**Existing defense:** The open P0 cap works. However, `deferred`, `accepted-risk`, `fixed`, `not-applicable`, and `suppressed` all enter the same resolved-status set, and those findings leave the penalty and cap calculations. [tools/checkyourself.py:201](../tools/checkyourself.py), [tools/checkyourself.py:1898](../tools/checkyourself.py), [tools/checkyourself.py:1981](../tools/checkyourself.py)

Even an authentic owner-approved deferral changes scheduling, not the exposure. This hole survives perfect compliance with approval rules.

**Fix direction:** Track workflow disposition separately from residual risk, retaining relevant penalties and launch blockers until mitigation or demonstrated non-applicability changes the underlying risk.

## 2. Evidence epistemics

My ranking below is qualitative: fabrication ease multiplied by damage if trusted.

| Rank | Artifact class | Fabrication / verification asymmetry | Current acceptance boundary |
|---|---|---|---|
| 1 | Waivers and applicability declarations | One sentence can remove a critical control or its risk penalty; verification requires understanding responsibility and authority. | Nonempty reason and resolved-status membership. `tools/checkyourself.py:1792`, `tools/checkyourself.py:1898` |
| 2 | Claimed restore, isolation, rollback, or CI execution receipts | Plausible output is cheap to write; verification requires reproducing behavior against the correct system state. | Coverage evidence is an array of strings. `schemas/coverage.schema.json:32` |
| 3 | Authentic receipts from the wrong revision or environment | A real success can support a false current claim; verification requires matching source, environment, and execution identity. | Coverage has project/date fields, while score output receives a new timestamp without requiring source-state binding. `schemas/coverage.schema.json:5`, `tools/checkyourself.py:2018` |
| 4 | Policies, runbooks, screenshots, and configuration files | Existence is relatively easy to verify; whether they demonstrate the claimed behavior is substantially harder. | The dogfood report credits screenshots and policy documents as Pass evidence. `02_RUN_DIAGNOSTIC/output/checkyourself-dogfood-production-reality-report.md:64`, `:80` |

**The trust chain bottoms out at the reviewer’s interpretation of reviewer-supplied text.** The scorer derives high confidence from coverage completeness and category statuses; it does not establish an independent observation of the cited behavior. [tools/checkyourself.py:2005](../tools/checkyourself.py)

The repository’s own retrofit notes identify source-state drift and distinguish worker, branch, release, and generated-proof states. Those distinctions have not become required provenance in the coverage contract. [docs/RETROFIT-LEARNINGS-2026-09-04.md:7](../docs/RETROFIT-LEARNINGS-2026-09-04.md), [schemas/coverage.schema.json:15](../schemas/coverage.schema.json)

A content hash alone would authenticate which bytes were presented. It would still leave the question: **why do those bytes prove this claim?** That is the unresolved part of finding #1.

## 3. The senior-engineer trust curve

### #5 — SEV-2: Precision and prescribed fixes outrun demonstrated knowledge

I followed the sample report linked from the README. [README.md:98](../README.md)

- **First glance:** The summary describes a plausible authorization risk and explicitly says server-side evidence is insufficient. I understand the uncertainty. [samples/sample-production-reality-report.md:9](../samples/sample-production-reality-report.md)
- **Stack table:** Database, authentication, and hosting remain weakly established. My expectation becomes a scoped investigation. [samples/sample-production-reality-report.md:15](../samples/sample-production-reality-report.md)
- **Score:** Suddenly I receive **42/100, Medium confidence**. The accompanying explanation names penalties but provides no numerical breakdown from which I can reconstruct 42. The precision becomes a claim I must trust. [samples/sample-production-reality-report.md:24](../samples/sample-production-reality-report.md)
- **First fix:** Missing proof of ownership checks becomes a recommendation to add ownership checks. The proposed batch begins implementation before the sample establishes whether the control exists. **This is where my trust dies:** the report has not yet distinguished a missing control from a missing observation. [samples/sample-production-reality-report.md:33](../samples/sample-production-reality-report.md), [samples/sample-production-reality-report.md:53](../samples/sample-production-reality-report.md)

Blocking launch on unverified authorization is defensible. Prescribing a control change requires additional knowledge.

**The single report change:** Put a compact claim-and-proof record before the score: what was directly observed, what is inferred, what remains untested, and the decisive check that would change the verdict.

**Fix direction:** Require each consequential verdict and proposed fix to distinguish demonstrated failure from missing verification, with a reproducible check supporting that distinction.

## 4. Naming, positioning, and AI-GEO

### #7 — SEV-2: The discovery surfaces sell a broader assurance than the executable contract provides

Keep **CheckYourself**. The problem is the promise attached to it.

The README’s first 160 characters repeat the category “AI production-readiness diagnostic for apps built with AI” before explaining the evidence mechanism. Later, the FAQ promises an engine that “finds every gap.” The machine-facing one-liner also leads with production readiness and a 0–100 score. [README.md:1](../README.md), [README.md:257](../README.md), [llms.txt:3](../llms.txt)

**My predicted LLM summary, based on those local surfaces:** “A model-agnostic framework that audits AI-built apps, scores production readiness, and guides fixes.”

That describes the category, but loses the useful distinction between a completion assertion and evidence supporting it. It also encourages interpreting a readiness score as broader assurance.

**An honest description today:** “A local production-audit workflow and deterministic scorer for reviewer-supplied findings and coverage.”

**The positioning to earn:** “CheckYourself turns ‘done’ into a reviewable record of verified behavior, assumptions, and unresolved risks.”

**Fix direction:** Align the README opening, skill description, and machine-facing summary around reviewable completion evidence, explicitly bounding what the current scorer verifies.

## 5. The missing capability: challenge a completion claim

### #8 — SEV-2: The core interface is not bound to what the user originally asked to accomplish

The advanced specification guidance already requires contracts before code and measurable acceptance criteria. The core scoring interface consumes findings and coverage; it does not require the original task, its acceptance criteria, or an executable challenge to its completion claim. [90_ADVANCED/capabilities/01-spec-driven-delivery/SKILL.md:57](../90_ADVANCED/capabilities/01-spec-driven-delivery/SKILL.md), [tools/checkyourself.py:2276](../tools/checkyourself.py)

Thought experiment: an agent builds a carefully secured export endpoint that exports the wrong records. Broad production controls can be present while the requested outcome remains unmet.

**The 10× capability is a verifier-owned challenge runner.** Freeze the accepted completion claim, derive a falsifiable challenge, and execute it against the captured source state using checks the builder cannot silently rewrite. Record what behavior the challenge establishes and what remains unproven; invalidate that receipt when relevant inputs change.

For “tenant isolation is fixed,” the useful result would be a captured attempt by tenant A to access tenant B’s object, tied to the tested revision and environment.

Independence comes from separate control over the challenge and receipt. Another model reviewing the same editable assertions does not establish that boundary.

**Fix direction:** Add claim-specific challenge execution that binds accepted task outcomes to independently captured results and explicit invalidation conditions.

## 6. Additional angle: discovering a defect can erase uncertainty

### #4 — SEV-1: Category folding lets a Finding override an unresolved Unknown

This is an executable defect, independent of fabricated evidence.

With otherwise identical synthetic inputs:

| State | Score | Confidence | Recovery unknown |
|---|---:|---|---|
| S06 recovery Unknown; S07 isolation Pass | 82 | low | Present |
| S06 unchanged; S07 becomes Finding with a P3 finding | 98 | high | Still present |

Both score artifacts passed schema validation.

The cause is explicit: `Finding` ranks above `Unknown` when surfaces collapse into a category. Evidence penalties and confidence gates subsequently inspect that collapsed status. The recovery question survives in `missing_evidence`, but loses its scoring effect and disappears from `manual_evidence_needed`. [tools/checkyourself.py:1772](../tools/checkyourself.py), [tools/checkyourself.py:1795](../tools/checkyourself.py), [tools/checkyourself.py:1824](../tools/checkyourself.py), [tools/checkyourself.py:1992](../tools/checkyourself.py)

Omitting the corresponding finding record entirely produced **100/high**: the coverage Finding itself creates no finding penalty. [tools/checkyourself.py:1929](../tools/checkyourself.py), [tools/checkyourself.py:1947](../tools/checkyourself.py)

**Fix direction:** Preserve unresolved evidence gaps independently of finding severity and require coverage Findings to reconcile with the findings register.

## 7. Additional angle: a valid report can contradict its own verdict

### #6 — SEV-2: Report validation establishes structure without establishing verdict consistency

I changed the existing golden report to **100/high**, removed its caps, and changed its finding to an **open P0**. Validation returned `valid: true`; regeneration and parsing preserved the contradictory verdict. [tests/test_checkyourself_cli.py:19](../tests/test_checkyourself_cli.py), [tools/checkyourself.py:2601](../tools/checkyourself.py), [tools/checkyourself.py:2613](../tools/checkyourself.py)

This is consistent with the documented schema-validation command. The trust problem appears when schema validity or successful round-tripping is treated as verification of the report’s conclusion: neither invokes the scorer to reconcile the verdict. [tools/checkyourself.py:2280](../tools/checkyourself.py), [tools/checkyourself.py:2627](../tools/checkyourself.py)

**Fix direction:** Add explicit semantic verification that recomputes the verdict and reconciles coverage, findings, caps, and backlog, keeping schema validity separately labeled.

## Findings table

| # | sev | finding | evidence file:line | fix direction |
|---|---|---|---|---|
| 1 | SEV-1 | Fabricated evidence references earn 100/high. | `tools/checkyourself.py:1597`, `:1788`, `:2011` | Reserve verified credit for checked provenance and claim support. |
| 2 | SEV-1 | Self-declared non-applicability earns full credit without evidence. | `tools/checkyourself.py:1792`; `02_RUN_DIAGNOSTIC/scoring-method.md:22` | Independently establish applicability and delegated responsibilities. |
| 3 | SEV-1 | Deferring or accepting a P0 removes its risk penalty and cap. | `tools/checkyourself.py:201`, `:1898`, `:1981` | Separate workflow disposition from residual risk. |
| 4 | SEV-1 | Adding a Finding overrides critical uncertainty and increases confidence. | `tools/checkyourself.py:1772`, `:1795`, `:1992` | Aggregate evidence gaps independently and reconcile Finding rows. |
| 5 | SEV-2 | The sample’s score and proposed fix outrun demonstrated knowledge. | `samples/sample-production-reality-report.md:24`, `:33`, `:53` | Lead with observed, inferred, and untested claims plus decisive checks. |
| 6 | SEV-2 | Schema-valid reports can contradict their own open P0 findings. | `tools/checkyourself.py:2601`, `:2613` | Add semantic verdict verification alongside structural validation. |
| 7 | SEV-2 | Discovery copy overstates assurance and obscures the evidence mechanism. | `README.md:1`, `:257`; `llms.txt:3` | Position around reviewable evidence with explicit verification limits. |
| 8 | SEV-2 | Core scoring is unbound to the original completion claim. | `tools/checkyourself.py:2276`; `90_ADVANCED/capabilities/01-spec-driven-delivery/SKILL.md:57` | Add verifier-owned challenges tied to accepted task outcomes. |

**THE ONE THING**
