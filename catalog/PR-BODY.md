Disclosure: the plugin's check tool runs one operator-approved test command (S11 from `.checkyourself/challenges.json`) inside the kanban task's workspace. That is project code running with the OS user's authority: it can read and write files, use the network and cost money. It is not a sandbox. Hermes asks for human approval before every run unless the operator allowlists the approval's rule. The plugin makes no model calls, sends no telemetry, reads no credential stores and runs no daemon.

## What it does
A `pre_tool_call` hook refuses `kanban_complete` until the task has a signed passing verdict whose workspace fingerprint still matches. The verdict comes from `checkyourself_evidence_check`, which runs the approved command with a pinned environment in its own process group, re-fingerprints the tree, and runs the bundled CheckYourself scanner (any P0/P1 finding blocks). The completion hook itself executes nothing.

The operator approves each project from their own shell (`hermes evidence-gate approve PROJECT`, preview then `--confirm DIGEST`). Approvals, the HMAC key and verdicts live in the profile's plugin-data directory, never in the project. With the plugin enabled but no project approved it is inert and logs one warning.

Bounds: it gates only the exact `kanban_complete` tool, not prose answers, external board clients or review handoffs. It proves the approved command passed on this tree, not that the tests are good. Processes running as the same OS user can edit its state.

## Provenance and proof
- Source: KyaniteLabs/checkyourself, subdir `hermes-plugin`, at the pinned sha in the catalog entry. The vendored engine is byte-checked against the repository by `tools/build_hermes_plugin.py`, which also fails on any unlisted file.
- Tested on Linux with Hermes `e76fbd80be65ea5c1b89831f8d7aaedb713f5cac` (manifest floor >=0.23.0). macOS and Windows are not supported.
- `hermes plugins validate`: ok, one warning for a private import. Hermes has no public API to read another task's workspace, so orchestrator completions use a read-only `hermes_cli.kanban_db` lookup; if it breaks, they fail closed.
- CI runs the plugin unit tests, `hermes plugins validate`, and `demo/native_demo.py` on the pinned Hermes runtime. The demo uses the real plugin loader, hook dispatch, approval gate, registered tool and registered CLI.

## Safety and rollback
Registration does no I/O. No new runtime dependencies. Keep `plugins.hook_callback_timeout` above 15 seconds (default 30). Rollback: disable the plugin. There is no board migration.
