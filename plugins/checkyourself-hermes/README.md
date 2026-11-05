# CheckYourself for Hermes (native plugin)

**Evidence Gate** — before you believe a completion claim, re-derive it with a local read-only scan, a deterministic 0–100 score, and a ranked backlog. Wraps `@puenteworks/checkyourself@1.7.0`.

| Surface | What it does |
|---|---|
| `pre_llm_call` | When a message looks like a completion / launch claim (`done`, `tests pass`, `ready to ship`, …), injects an Evidence Gate brief |
| `post_tool_call` | Appends `checkyourself_*` summaries (tool, ok, score / finding counts — **no file contents**) to a score ledger |
| `/checkyourself describe\|scan\|score\|backlog\|next\|coverage\|status\|help` | Gateway-safe by default: project ops refused on gateway unless `allow_project_slash_on_gateway: true`. Never exposes `challenge` / `init` / `mcp` / `receipt` / `diff` |
| `checkyourself_scan` | Read-only scan (`--no-write`); saves JSON under plugin-data |
| `checkyourself_score` | Production Reality Score from findings (last scan by default) |
| `checkyourself_backlog` | Ranked remediation backlog |
| `checkyourself_next` | Next highest-severity approval batch |
| `checkyourself_describe` | Capability manifest |
| `checkyourself_coverage` | 20-surface coverage skeleton |
| Skill `checkyourself:checkyourself` | Claim → scan → score → verdict workflow |

## Install

```bash
hermes plugins install KyaniteLabs/checkyourself --subdir plugins/checkyourself-hermes
hermes plugins enable checkyourself
```

Requires **Node ≥ 18**, `npx` on PATH, and **Python 3** (the npm package is a trampoline to a stdlib-only Python CLI).

## Disclosure

- **Downloads code:** first use runs `npx -y @puenteworks/checkyourself@1.7.0` (npm). Override with `checkyourself_command` (e.g. `checkyourself` after `npm i -g @puenteworks/checkyourself@1.7.0`).
- **Network / telemetry:** the CLI itself is local-first — no network calls, no telemetry, secret values never printed. The only network step is the one-time npm download of the pinned package (or whenever the npx cache misses).
- **Filesystem:** `scan` is read-only against the target project (`--no-write`). Immutable session/project-bound scan receipts, the per-session implicit pointer, and the score ledger live under `<HERMES_HOME>/plugin-data/checkyourself/` (per profile). Any failed scan attempt (bad path/arguments, missing executable, subprocess error, non-zero CLI) invalidates that session's implicit receipt. Explicit receipt inputs are unpacked only into a unique temp under plugin-data and removed after the call; raw CLI findings files (including `[]` arrays) are passed through untouched. Nothing is written into the scanned project or any caller-owned input directory by this plugin. On timeout the whole child process group is SIGTERMed, then any survivors are SIGKILLed after a short grace.
- **Secrets:** child env is scrubbed (PATH/HOME/locale/proxy/npm cache/`CHECKYOURSELF_PYTHON` only). No API keys are required or copied from Hermes secret scope.
- **Gateway:** `/checkyourself scan|score|backlog|next|coverage` are refused on gateway platforms unless `allow_project_slash_on_gateway: true`. Agent tools still work.
- **Not in v0.1.0:** `challenge` (executes committed challenge commands), `init` (writes starter files), `mcp` (stdio server), `receipt`, `diff` — use the CheckYourself CLI directly.
- **No background jobs;** nothing runs unless a hook matches or you call a tool/slash.

## Settings (`plugins.entries.checkyourself.settings`)

| Key | Default | Notes |
|---|---|---|
| `checkyourself_command` | `npx -y @puenteworks/checkyourself@1.7.0` | CLI prefix |
| `default_project` | `.` | Used when scan omits `project` |
| `inject_on_claim` | `true` | pre_llm_call Evidence Gate brief |
| `allow_project_slash_on_gateway` | `false` | gateway safety |
| `max_files` | `6000` | scan truncation |
| `timeout_seconds` | `180` | per CLI call |

## Known issues

- First call is slow (npm download); offline machines need a pre-installed `checkyourself` on PATH.
- Score without a prior valid session receipt fails with a clear error — run `checkyourself_scan` first (or pass `findings_path`). Relative project paths resolve via Hermes session cwd (`resolve_agent_cwd`).
- Large repos may truncate at `max_files`; the scan JSON discloses truncation in `scan_limits`.
- The score is **scoped evidence**, not a production-safety certification.
- No Desktop pane, 2:1 banner, or screenshots yet.
- Local validate may run on Hermes &lt; 0.21.6; catalog floor remains `>=0.21.6`.

## Demo (&lt; 90s)

```text
/checkyourself describe
/checkyourself scan /path/to/app
/checkyourself score
/checkyourself next
```

Or ask the agent: "We claim this app is ready to ship — run the Evidence Gate."

License: Apache-2.0 (same as CheckYourself).
