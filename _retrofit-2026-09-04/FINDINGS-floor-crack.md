# FLOOR OPINION — lane 'floor-crack' (CRACK-Ornith) on checkyourself
# via bridge :8817, 34s, source=content

# CRACK-Ornith on `checkyourself`

## 1. What does it do (2 sentences)?
It's a read-only-first production-readiness diagnostic that sweeps an AI-built app's whole launch surface, turns it into a scored **Production Reality Report** (0–100 with severity caps), and only then guides you through fixing the *safest first batch* — code stays untouched until you approve. It pairs a deterministic Python scanner pipeline (`scan → coverage → score → backlog → next → diff`) with a human-in-the-loop fix loop and a gap-driven learning plan.

## 2. Where would you get stuck?
- **The scoring isn't self-contained.** The skill keeps pointing at `coverage-matrix.md` and `scoring-method.md` — but those files aren't in the definition. Read it alone and you can't actually compute a number; you can only *reference* a method you haven't been shown.
- **The severity caps don't compose.** P0 caps at 49, P1 at 74, missing-critical-evidence at 84, missing-launch-gate at 90 — but nothing says how those stack, in what order, or against what base score. "Caps apply even to estimates" is a promise, not an algorithm.
- **The manual fallback loses the determinism.** If `tools/checkyourself.py` is missing, you're told to sweep by hand and call the score "hand-computed" — but stable semantic rule IDs (`CY-SECRET-001`) and reproducible diffs are the whole value prop, and the fallback never guarantees them.
- **"Pass requires evidence" is circular without a rubric.** You're told Unknown ≠ Pass, but nothing defines *how much* evidence qualifies. Every reviewer will pass/unknown differently.

## 3. Top 5 problems
1. **Scoring methodology is external, not internal.** The heart of the product — the number — lives in files the skill assumes exist. Ship the rubric inline or the score is hand-waved.
2. **Severity caps are stated, not defined.** No precedence rules, no interaction model between the four caps. Two runs of the same app could land at 51 and 73.
3. **Evidence standard is asserted, not operationalized.** "Pass requires evidence / Finding requires evidence and risk" is good philosophy, zero rubric. Same words, different judgments.
4. **Scope is huge and fuzzy.** Product, frontend, a11y, backend, auth, migrations, secrets, CI/CD, deps, deploy, observability, perf, privacy, compliance, *and* AI/RAG/agent governance — all "when relevant." "When relevant" becomes a catch-all for coverage you skip and can't defend.
5. **"Safest first batch" has no formula.** Reversibility + low blast radius is named but not measured, so "safest" becomes opinion dressed as output.

## 4. Vote: **GOOD-ENOUGH** (with a clear path to AMAZING)

**Why:** The *philosophy* is excellent and rare — read-only first, evidence-over-vibes, severity caps, guided remediation, and a learning plan that ties lessons to actual gaps. The voice is sharp without being a jerk, and "Demo-ready is not launch-ready. Here is the receipt." is a genuinely good line. What holds it back is that it's a **great process spec with a thin engine**: the scoring, evidence rubric, and safety-scoring are all pointed at files that aren't there. Fix those three and it's AMAZING; ship it as-is and reviewers will disagree on the number, which is the one thing a production-readiness tool cannot afford.

**Push it to AMAZING by:** (a) inlining the coverage matrix + scoring method, (b) defining cap precedence and the base→cap formula, (c) giving a concrete evidence bar per check type, and (d) bounding scope with a "must-verify for your risk level" gate instead of sweeping everything every time.
