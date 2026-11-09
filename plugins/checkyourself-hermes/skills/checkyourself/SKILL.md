---
name: checkyourself
description: >-
  Use when completed work makes claims — "done", "tests pass", "it works", "ready
  to launch" — that must be verified before they are believed. Re-derive each claim
  with CheckYourself Hermes tools (scan → score → backlog/next) and report
  CONFIRMED / REFUTED / UNVERIFIABLE with evidence. Fast claim-verification by
  default; deeper Production Reality Score when launch stakes justify it.
---

# CheckYourself (Hermes plugin)

The job: independently re-derive the claims completed work makes about itself and
report each as CONFIRMED, REFUTED, or UNVERIFIABLE with evidence — so "done" means
proven, not asserted. Never grade your own homework from memory: the author's
summary is a claim to check, never evidence for itself.

## Hermes surfaces

Prefer these when running inside Hermes (registered as `checkyourself:checkyourself`):

- Tool `checkyourself_scan` — read-only project scan (`--no-write`); saves findings in plugin-data.
- Tool `checkyourself_score` — Production Reality Score (0–100) from last scan or a findings path.
- Tools `checkyourself_backlog` / `checkyourself_next` — ranked remediation + next approval batch.
- Tools `checkyourself_describe` / `checkyourself_coverage` — capability manifest / 20-surface skeleton.
- Slash `/checkyourself …` — same paths; project ops refused on gateway unless opted in.
- Hook `pre_tool_call` — blocks `kanban_complete` (and any other name in `completion_tools`) until `checkyourself_score` returns a numeric score with no open P0 or P1. Missing evidence blocks. A passing gate is scoped evidence, not a launch certificate.

Not exposed here: `challenge`, `init`, `mcp`, `receipt`, `diff` — use the CheckYourself CLI.

## Workflow

1. **Extract the claims.** From the completion report, commit message, diff, README, or request. Make implicit claims explicit.
2. **Scan.** `checkyourself_scan` on the project root (set `deep: true` when stakes are high).
3. **Score.** `checkyourself_score` (optionally pass `claim`). Treat the number as scoped evidence, not a safety cert.
4. **Prioritize.** `checkyourself_backlog` / `checkyourself_next` for the remediation path.
5. **Label with evidence:** CONFIRMED / REFUTED / UNVERIFIABLE (never silently drop).
6. **Report verdict-first.** One line on whether the completion claim is true, then counts, then evidence. Stay read-only unless the user approves a named fix.

## Limits

- Stay read-only by default. No dependency installs, secret rotation, or production changes without an explicitly approved named fix.
- No secrets, customer data, or unredacted `.env` values in output.
- For regulated, financial, health, legal, life-safety, security-critical, or high-volume systems, recommend qualified expert review.
- When the verifier is the same agent that did the work, say so and discount accordingly.
