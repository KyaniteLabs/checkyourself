# FACTS — checkyourself retrofit gauntlet (dossier, READ-ONLY stage)
- Product: CheckYourself — production-readiness diagnostics + guided remediation for AI-built apps.
- Repo root: . (your cwd = repo root). Layout: 00_START_HERE, 01_PROJECT_CONTEXT, 02_RUN_DIAGNOSTIC, 03_GUIDED_FIX_MODE, 04_LEARNING_PLAN, 05_OUTPUT_TEMPLATES, 06_ADAPTERS, 10_DASHBOARD, 90_ADVANCED, skills/, tools/, tests/, docs/, reference/, samples/, schemas/, assets/.
- Skill entry (the user-facing contract): skills/checkyourself/SKILL.md (109 lines). Its described CLI: tools/checkyourself.py with subcommands describe/scan/coverage/score/backlog/next/diff (--ci regression gate).
- Tests: tests/test_checkyourself_cli.py, tests/test_validate_public.py (discover runner: try `python3 -m pytest tests/ -q`, fallback `python3 -m unittest discover tests`; record what actually ran).
- Other public surfaces: README.md, START_HERE.md, PASTE_THIS_INTO_YOUR_AI.md, llms.txt, identity.md, rules.md, CONTEXT.md, AGENTS.md, checkyourself.manifest.json, glama.json, Dockerfile.
- History: skill last touched 2026-06-12 (v1.7.0 docs pass); repo got unrelated cap-enrichment PRs in Aug. Built by older models — assume drift everywhere.
- Constraints: STAGE-1 = AUDIT ONLY. Do NOT modify, create, or delete ANY file outside _retrofit-2026-09-04/. No network. No new dependencies. Never print secrets (there should be none; flag if found).
- Output contract: write EXACTLY ONE file: _retrofit-2026-09-04/FINDINGS-<ROLE>.md — header (verdict RETROFIT-NEEDED yes/no + one line), findings list (ID, severity P0-P3, file:line evidence verbatim, why it matters, fix sketch), coverage list (what you swept), unknowns. No prose padding.
