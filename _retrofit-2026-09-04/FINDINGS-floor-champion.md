# FLOOR OPINION — lane 'floor' (model Qwen3.8-27B) on checkyourself
# via engines bridge :8817, 49s

1. **What does this product do?**
It acts as a read-only production-readiness auditor that scans AI-built apps to generate a scored "Production Reality Report" with evidence-backed findings. It then guides the user through a safe, approved remediation loop to fix issues before launch.

2. **Where would I get stuck or confused?**
*   **The "Context" Ambiguity:** Step 1 says to start with `CONTEXT.md` if present, but doesn't define what happens if *only* some of those files exist. Do I proceed with partial context or halt?
*   **The Python Dependency Trap:** Step 2 says "If `tools/checkyourself.py` exists," but doesn't specify what to do if it *doesn't* exist but the user expects a deterministic score. The fallback "sweep manually" is vague for a skill that promises "stable, semantic rule IDs."
*   **Scoring Cap Logic:** The caps (P0=49, P1=74, etc.) are listed, but it’s unclear how they interact with the "evidence caps." If I have a P0 *and* missing critical evidence, do I take the lower cap? The interaction isn't explicitly defined.
*   **The "Dashboard" Trigger:** It says "If the user says `dashboard yes`," but doesn't specify if this is a strict string match or a semantic intent. If I say "show me a dashboard," does it trigger?
*   **Backlog vs. Next Steps:** Step 4 asks for a "complete ranked remediation backlog" AND a "safest first approval batch." Step 7 mentions a "learning plan." It’s unclear if the "learning plan" is part of the initial report or a separate artifact generated *after* fixes.

3. **Top 5 problems:**
*   **Vague Fallback for Missing Tools:** The skill relies heavily on `tools/checkyourself.py` for deterministic scoring. If that file is missing, the "manual sweep" instruction is too weak to guarantee the "stable rule IDs" promised in the overview. This breaks the core value prop of reproducibility.
*   **Unclear Scoring Interaction:** The severity caps and evidence caps are listed separately, but the logic for combining them (e.g., `min(severity_cap, evidence_cap)`) is not explicitly stated. This leads to inconsistent scoring.
*   **Overloaded Initial Report:** Step 4 asks for an executive summary, stack detection, unknowns, score, coverage sweep, findings, evidence table, backlog, first batch, questions, *and* learning plan seeds. This is a massive output for a single "read-only" pass. It risks diluting the critical P0/P1 findings with noise.
*   **Ambiguous "Approval" Boundary:** Step 5 says "Do not modify files until the user approves a specific fix or batch." Step 6 says "After approval, run the guided fix loop." It’s unclear if the "approval" is for the *entire* first batch or individual items within it. This could lead to over-acting or under-acting.
*   **Missing "Not Applicable" Justification:** While it says "Not applicable requires a reason," it doesn't specify *where* that reason goes in the report structure. Is it in the coverage
