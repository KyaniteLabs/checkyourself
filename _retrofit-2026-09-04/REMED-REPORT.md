# Remediation Report — W9/W10 Re-vote

Status: DONE

## Per-item status and evidence

| Item | Status | Evidence |
|---|---|---|
| MR-026 | fixed | `06_ADAPTERS/native-cli-mcp.md` is the canonical native CLI/MCP adapter. `06_ADAPTERS/README.md` identifies provider files as deltas. The adapter documents `describe`, `CHECKYOURSELF_SCAN_ROOT`, `--no-write`, explicit write targets, and approval boundaries. `docs/cli.md` and `docs/mcp.md` link to it. |
| MR-029 | fixed | `llms.txt` now identifies `rules.md` as the workflow authority and `docs/cli.md` as the canonical detector-rule registry. `docs/cli.md` labels that registry explicitly. |
| MR-030 | fixed | `docs/agent-access-cli-plan.md` now calls the scoring algorithm a current contract, marks the interface delivered, records current v1.7.0 context, and states the canonical resolution statuses without a separate `blocked` status. |
| MR-031 | fixed | `docs/agent-access-cli-plan.md` now matches the executable behavior: `NotApplicable` with a concrete reason retains its category weight and does not redistribute the denominator. |
| MR-032 | fixed | `05_OUTPUT_TEMPLATES/production-reality-report.md` backlog rows now require `Impact / blast radius` and `Files/systems touched`. The skill requirement names both fields. |
| MR-033 | fixed | `05_OUTPUT_TEMPLATES/README.md`, `10_DASHBOARD/README.md`, and `10_DASHBOARD/CONTEXT.md` document both `dashboard yes` and `dashboard inline`, with their HTML/CSS versus Markdown behavior. |
| MR-034 | fixed | `SECURITY.md` names the supported tagged `1.7.x` line, latest tagged release `1.7.0`, supported public `main`, and unsupported older tags. `tests/test_validate_public.py` checks the policy against the manifest version. |
| MR-036 | fixed | `02_RUN_DIAGNOSTIC/coverage-matrix.md`, `02_RUN_DIAGNOSTIC/scoring-method.md`, `02_RUN_DIAGNOSTIC/CONTEXT.md`, and the report template map prose `Not applicable` to JSON `NotApplicable`. |
| MR-038 | fixed | `skills/checkyourself/SKILL.md` adds the canonical manual rule-ID registry, reuse rule for shipped detector IDs, and evidence rubric for Pass, Finding, Unknown, and Not applicable. |
| MR-039 | fixed | `02_RUN_DIAGNOSTIC/scoring-method.md` and `skills/checkyourself/SKILL.md` state the base-score/minimum-cap formula and link the executable CLI contract and implementation. |
| Retrofit validator links | fixed | Link-like diagnostic examples were de-markdownized in `FINDINGS-luna-a.md` and `FINDINGS-luna-b.md`; no retrofit finding link is now treated as a broken public link. |

## Verification receipts

`python3 tools/validate_public.py`

```text
OK: public CheckYourself validation passed
Path: /Users/simongonzalezdecruz/workspaces/checkyourself
```

`python3 -m pytest tests/ -q`

```text
............................................ [ 45%]
............................................... [ 93%]
......                                                                   [100%]
97 passed, 53 subtests passed in 16.68s
```

## Changed-file list

- `02_RUN_DIAGNOSTIC/CONTEXT.md`
- `02_RUN_DIAGNOSTIC/coverage-matrix.md`
- `02_RUN_DIAGNOSTIC/scoring-method.md`
- `05_OUTPUT_TEMPLATES/README.md`
- `05_OUTPUT_TEMPLATES/production-reality-report.md`
- `06_ADAPTERS/README.md`
- `06_ADAPTERS/chatgpt.md`
- `06_ADAPTERS/claude-projects.md`
- `06_ADAPTERS/cursor-windsurf.md`
- `06_ADAPTERS/local-agents.md`
- `06_ADAPTERS/native-cli-mcp.md`
- `06_ADAPTERS/replit-lovable-bolt.md`
- `10_DASHBOARD/CONTEXT.md`
- `10_DASHBOARD/README.md`
- `SECURITY.md`
- `docs/agent-access-cli-plan.md`
- `docs/cli.md`
- `docs/mcp.md`
- `llms.txt`
- `skills/checkyourself/SKILL.md`
- `tests/test_documentation_contract.py`
- `tests/test_validate_public.py`
- `_retrofit-2026-09-04/FINDINGS-luna-a.md`
- `_retrofit-2026-09-04/FINDINGS-luna-b.md`
- `_retrofit-2026-09-04/REMED-REPORT.md`

No Git commands, installs, or network access were used.
