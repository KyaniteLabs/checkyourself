# Catalog PR draft — CheckYourself Evidence Gate

Maintainer opens this. This file is the draft text only. It is not an opened catalog pull request, and it does not publish npm.

Suggested title: `checkyourself: native Evidence Gate (plugin.yaml + completion score gate)`

Suggested target: the Hermes plugin catalog repository, subdir `plugins/checkyourself-hermes` from `KyaniteLabs/checkyourself`.

## Body to paste

Disclosure — the plugin shells out to the pinned CLI `npx -y @puenteworks/checkyourself@1.7.0` (Node >= 18 and Python 3; the npm package is a trampoline to a stdlib Python CLI). The first npx fetch downloads that exact package. The CLI itself is local-first: no telemetry and no secret values printed. Child environment is scrubbed. Scan uses `--no-write`. Receipts and the score ledger stay under `<HERMES_HOME>/plugin-data/checkyourself/`. Project slash commands are refused on gateway platforms unless `allow_project_slash_on_gateway` is true. `challenge`, `init`, `mcp`, `receipt`, and `diff` are not exposed. This is not a sandbox. npm publish stays CEO-gated and is not part of this draft.

## Native value

Native `plugin.yaml` plus hooks, not an MCP-only listing.

- `pre_llm_call` injects an Evidence Gate brief when a message looks like a completion claim.
- `pre_tool_call` is the completion gate. It blocks `kanban_complete` (override with `completion_tools`) unless CheckYourself returns a numeric score with no open P0 or P1. Missing evidence blocks. An open P0 or P1 blocks, and the block message includes the score. A passing gate is scoped evidence, not a launch certificate, and it does not re-run project challenge commands.
- `post_tool_call` appends score and finding-count summaries only.
- `/checkyourself` and the `checkyourself_*` tools wrap the same CLI.

Gateway slash identity uses the native session id, or the namespaced session key when the slash dispatcher has a key and an authoritative empty session id. It does not revive `HERMES_SESSION_ID` from the process environment after the native helper returned empty, and it does not share a `nosession` pointer. If the implicit-pointer write fails, the plugin does not claim the old receipt was invalidated; implicit scoring stays fail-closed until a new scan commits.

## Proof the maintainer can cite

- Product repo: `KyaniteLabs/checkyourself`, plugin subdir `plugins/checkyourself-hermes`.
- Pin the catalog entry to the product commit Maintainer chooses after this product PR is reviewed. Do not invent a SHA in this draft.
- Demo: `plugins/checkyourself-hermes/demo/gate_demo.py` and `demo/90-seconds.md`. It must print `PASS` and `elapsed_seconds` under 90. It uses the repo CLI, a temp `HERMES_HOME`, and no network.
- Tests: `python3 -m unittest tests.test_checkyourself_hermes_plugin`.
- Full repo check: the product PR’s Validate CheckYourself workflow on the exact head.
- Do not claim a fresh `hermes plugins validate` receipt here unless that command was run on a disposable `HERMES_HOME`. Do not run `hermes update`, restart a gateway, or point this at a live host.

## Safety / rollback

Import and `register()` only register hooks, tools, the slash command, and the skill. Disable or remove the plugin to roll back. No board schema changes. Set `completion_tools` to an empty string to turn the gate off without removing the scan tools. No production activation is performed by this draft.

This file is a prepared body, NOT an opened catalog PR.
