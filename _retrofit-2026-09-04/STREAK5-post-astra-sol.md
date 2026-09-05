Status: DONE_WITH_CONCERNS

Pinned state: branch `retrofit/2026-09-04`, HEAD `29c6a5898054942e3f6853ac4fb644f5d55ea8c8`.

Acceptance chain:

- `python3 -m pytest tests/ -q`: PASS — 120 passed, 86 subtests passed.
- `python3 tools/validate_public.py .`: PASS.

ASTRA cheat re-attempts (fresh, in-memory, no repository writes):

- Invented evidence receipts: fail closed — 29/100, low confidence, caps 84/90, all ten categories require evidence.
- Blanket reason-only `NotApplicable`: fail closed — 29/100, low confidence, caps 84/90, all ten categories require evidence.
- Accepted-risk P0: fail closed — 29/100, low confidence, P0 cap 49, finding remains scored, residual risk remains open.
- S06 Unknown plus S07 minor Finding: fail closed — 82/100, low confidence, critical-evidence cap 84, C1 remains in manual evidence requirements.

Findings:

1. SEV-1 — An authentic but irrelevant file can be laundered into universal evidence. I reused `README.md` plus its correct SHA-256 and caller-authored `origin`, `source_state`, and `result` for every Pass row. The scorer returned 100/high with no caps or evidence requests. The same irrelevant receipt used as every delegation receipt made blanket `NotApplicable` return 100/high. `_verify_receipts` proves file existence/hash and non-empty provenance strings, but it does not establish verifier ownership, freshness, surface-specific relevance, or truth of the claimed result (`tools/checkyourself.py:1526-1614`). This preserves the core fabricated-proof failure through a slightly less lazy strategy.

2. SEV-1 — A coverage `Finding` can disappear when linked to any registered resolved finding. I set S07 to `Finding`, linked it to a fixed P0, and supplied otherwise accepted coverage. The scorer returned 100/high, awarded all 18 C1 points, applied no caps, and scored no findings. The suppression check tests linkage against all registered IDs rather than unresolved findings (`tools/checkyourself.py:2122-2128`), while `Finding` itself has no direct category penalty. This is a new false-green path in the ASTRA #4 reconciliation logic.

No acceptance regression was observed outside these adversarial false-green paths.

## IMPROVEMENTS

1. Make receipts verifier-issued and surface-bound. WHY: caller-authored provenance plus a real irrelevant file still earns 100/high. FIX: sign or independently generate receipts with immutable source revision, command/environment, surface ID, result, and expiry; reject reuse across unrelated claims.
2. Reconcile coverage Findings only with unresolved linked findings. WHY: linking a Finding row to a fixed ID suppresses every penalty. FIX: intersect against unresolved IDs and independently penalize or block any Finding row whose live linked finding set is empty.
3. Add both probes as regression tests. WHY: the current 120-test suite passes while both 100/high exploits remain. FIX: assert irrelevant receipt reuse and Finding-to-fixed linkage cannot exceed the applicable cap or high confidence.

FULLY-GREEN: no
