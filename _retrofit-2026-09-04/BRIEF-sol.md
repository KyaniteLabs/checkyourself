# ROLE: CHIEF AUDITOR (codex-sol-high) — checkyourself stage-1
Read _retrofit-2026-09-04/FACTS.md first; it is authoritative.
Your lens: SYSTEMIC + ARCHITECTURE. You own the master view:
1. Does the product do what skills/checkyourself/SKILL.md promises? Map EVERY promise in the skill (CLI subcommands, scoring caps, rule IDs, report fields, dashboard modes, safety rules) to actual code in tools/checkyourself.py + templates. Every unimplemented/drifted promise = finding with both sides quoted.
2. Architecture defects: dead code paths, broken imports, schema/manifest vs reality, Dockerfile vs actual runtime, adapters (06_ADAPTERS) vs current model surfaces, scoring-math correctness (severity caps logic), diff/--ci gate correctness.
3. Test honesty: run the tests (FACTS §tests). Any test that can't run, tests that assert nothing, coverage of the promised pipeline.
4. Master fix plan: order every finding into fix-waves (P0 first), each wave independently verifiable.
Be exhaustive — this is a full-intensity retrofit audit; the CEO standard is "no bugs, everything amazing." Audit-only: write ONLY _retrofit-2026-09-04/FINDINGS-sol.md.
