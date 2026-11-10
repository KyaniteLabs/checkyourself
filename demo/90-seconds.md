# Gate-first demo (about 75 seconds)

0-10s: "A completion claim is not proof." Show `kanban_complete` refused with `NO_VERDICT`.
10-25s: The operator approves the scratch project from their own shell: preview, then `--confirm DIGEST`. The same command inside a worker is refused.
25-40s: The agent calls `checkyourself_evidence_check`. Headless, Hermes's approval gate refuses it. The operator adds the printed `plugin_rule:` line to `command_allowlist`.
40-55s: The check runs the approved tests and the scanner and records `ALLOWED`. `kanban_complete` now passes, and the hook executed nothing.
55-65s: Edit one workspace file. `kanban_complete` is refused with `STALE_TREE`.
65-75s: Close on the disclosure: the check runs approved project tests with your OS user's authority. It is not a sandbox.

## Capture notes
- Terminal at 120x32, a fresh scratch `HERMES_HOME`, no real project or credentials.
- Source of every step: `demo/native_demo.py`, run by the runtime test command in `hermes-plugin/README.md`.
- Crop absolute paths. Captions and a transcript; no rapid cuts.
