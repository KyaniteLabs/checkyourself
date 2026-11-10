# Check Yourself Evidence Gate

An agent saying "done" is not proof. This Hermes plugin refuses `kanban_complete` until a test command the operator approved has passed on the task's workspace, and the workspace has not changed since.

**Disclosure first.** The check runs the operator-approved test command (S11 from `.checkyourself/challenges.json`) inside the task workspace. That is project code running with your OS user's authority: it can read and write files, use the network and cost money. It is not a sandbox. Hermes asks for approval before every run unless you allowlist it. Approve only projects whose tests you would run yourself. The plugin makes no model calls, sends no telemetry, reads no credential stores and runs no daemon.

## How it works

1. The operator approves a project once, from their own shell: `hermes evidence-gate approve /path/to/project`. The preview shows the exact argv, the resolved executable and its SHA-256, the pinned environment (`PATH`, `HOME`, `LANG`, `LC_ALL` from the operator's shell, plus `PYTHONDONTWRITEBYTECODE=1`, `PYTHONNOUSERSITE=1` and `PYTEST_ADDOPTS=-p no:cacheprovider`), the time limit and a digest. Re-run with `--confirm DIGEST` to record it. `--prefix DIR` makes the approval cover every task worktree under `DIR` whose S11 is identical.
2. The agent calls `checkyourself_evidence_check`. The plugin's `pre_tool_call` hook escalates that call to Hermes's human-approval gate (`rule_key` `checkyourself-evidence-check:<digest16>`). With no human present it fails closed, unless the profile already waives approvals (`approvals.mode: off`, yolo, or a cron, single-query or unattended-platform mode set to `approve`). To let headless kanban workers run it, add `plugin_rule:checkyourself-evidence-check:<digest16>` (printed by `approve`) to `command_allowlist` in `config.yaml`. Re-approving with a different command or environment changes the digest, so the old allowlist line stops matching.
3. The check fingerprints the workspace, runs the approved argv in its own process group with only the pinned environment, fingerprints again, and runs the bundled CheckYourself scanner. It records a signed verdict for this board and task.
4. `kanban_complete` executes nothing. The hook checks that the verdict's signature, task, workspace and approval digest match, that it passed, and that the workspace fingerprint is unchanged.

A pass needs all of these:

- The project's current S11 equals the approved S11, and the executable's path and SHA-256 are unchanged.
- The command exits 0 and its output matches `regex_match` (when set), within `min(timeout_s, max_run_s)` (default 120 seconds). On timeout the whole process group gets SIGTERM, then SIGKILL.
- No file in the workspace changed during the run.
- The scanner reports no P0 or P1 finding. Project suppressions are ignored; only ids the operator passed with `--accept-finding` are excepted. `known_blockers` from the agent can add blockers, never remove them.

Each verdict is in one explicit state, and the block message says whether the agent or the operator has to act:

| State | Meaning |
| --- | --- |
| `INERT_UNCONFIGURED` | Plugin enabled but never configured. Completions are allowed and one warning is logged. |
| `NOT_ENROLLED` | The task has no workspace, or no approval covers it. Allowed. |
| `ALLOWED` | A passing verdict matches the current tree. |
| `NO_TASK`, `NO_VERDICT`, `STALE_TREE`, `TESTS_FAILED`, `TIMEOUT`, `FINDINGS_BLOCK`, `TREE_CHANGED_DURING_RUN`, `RUN_ERROR` | Agent-side: fix and run the check again. |
| `WORKSPACE_UNRESOLVED`, `VERDICT_TAMPERED`, `APPROVAL_CHANGED`, `FINGERPRINT_TIMEOUT`, `CONFIG_INVALID`, `RETRY_CAP_REACHED` | Operator-side. |

After `max_attempts` executed checks (default 5) for one task, the check refuses to run until the operator runs `hermes evidence-gate reset TASK [--board B]`. Other commands: `status [PROJECT]` and `revoke PREFIX`. `approve`, `revoke` and `reset` refuse to run inside a kanban worker (`HERMES_KANBAN_TASK` set). That refusal is a speed bump, not a boundary.

## Where state lives

The HMAC key (mode 0600), `approvals.json` and `verdicts/` live in the profile's plugin-data directory (`$HERMES_HOME/plugin-data/<plugin>/`), never in the project. Each Hermes profile has its own approvals. The task and workspace come from the dispatcher's `HERMES_KANBAN_TASK`, `HERMES_KANBAN_BOARD` and `HERMES_KANBAN_WORKSPACE`, or from a read-only lookup on the board when a caller names `task_id`. `requires_env` is empty because none of these are operator settings. The board lookup (for orchestrators completing another task) reads the board database read-only through `hermes_cli.kanban_db`, which Hermes has no public plugin API for, so `hermes plugins validate` warns about that one private import. If a Hermes release breaks it, those completions fail closed with `WORKSPACE_UNRESOLVED`.

## What it does not defend

- **Same-OS-user access.** Anything that can run shell commands as the Hermes user can edit plugin-data, `config.yaml` or the key. Run untrusted agents under a different OS user or a sandbox.
- **Code outside the workspace.** Only the workspace is fingerprinted, plus the targets of symlinks that leave it. Interpreters, virtualenvs and system packages are not, apart from the S11 executable's hash.
- **Weakened tests.** An agent can delete or weaken tests inside the workspace. The verdict proves the approved command passed on this tree, not that the tests are good. Review still matters.
- **Escaping processes.** A child that calls `setsid` leaves the process group and survives a timeout kill.
- **Other completion paths.** Only the exact `kanban_complete` tool is gated, not prose answers, external board clients or `kanban_request_review`.
- Fingerprints use `lstat` metadata (including ctime and inode), not content hashes. Any write changes ctime, but copying a workspace means checking again.
- Any concurrent edit, including by tests that write into the workspace, invalidates the verdict (`TREE_CHANGED_DURING_RUN` or `STALE_TREE`). Use `--ignore PATH` for build output that tests write. `.git` is always ignored.

## Install and limits

Linux only, tested on Hermes 0.23.0+48 at `e76fbd80be65ea5c1b89831f8d7aaedb713f5cac`. macOS and Windows are not supported. Install from the catalog entry, then `hermes plugins enable checkyourself-evidence-gate`.

The completion hook only reads files and fingerprints the tree, within `hook_budget_s` (10 seconds). Hermes's default `plugins.hook_callback_timeout` is 30 seconds. Keep it above 15 seconds. A slower hook is suppressed and Hermes then fails every `pre_tool_call` closed. The test run happens inside the tool call, not the hook. Registration does no I/O. To roll back, disable the plugin. There is no board migration.

## Reproducible source

`tools/` holds a byte-for-byte copy of the CheckYourself engine (`tools/checkyourself.py` and `tools/checkyourself/`) and `LICENSE`. `python3 tools/build_hermes_plugin.py` (run from the repository root) fails if any vendored file differs from the repository's engine or if the plugin contains a file that is not on its list. `--write` refreshes the copy from the working tree. No network, no new runtime dependency, no compiled files.

```sh
python3 tools/build_hermes_plugin.py
python3 -I -B -m unittest discover -s tests -p test_hermes_plugin.py -v
hermes plugins validate hermes-plugin --json
# Real Hermes runtime, fresh scratch profile:
CHECKYOURSELF_RUNTIME_TEST=1 HERMES_HOME="$(mktemp -d)" /path/to/hermes/.venv/bin/python -m unittest discover -s tests -p test_hermes_runtime.py -v
```

To gate this repository itself, approve it with `--ignore tools/checkyourself/__pycache__`: a packaging test deliberately writes bytecode there. Its S11 (the full suite) then passes in about 45 seconds.

The runtime demo (`demo/native_demo.py`) installs the plugin into the scratch profile and drives the real Hermes plugin loader, hook dispatch, approval gate, registered tool and registered CLI: approval refused inside a worker, approved from the operator shell, completion blocked without a verdict, check refused headless, rule allowlisted, check passes, completion allowed, a file changes, blocked again.
