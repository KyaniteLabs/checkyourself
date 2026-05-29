# 00 — Start Here

CheckYourself has these user-facing layers:

1. **Folder diagnostic** — best default, using this folder as your AI's operating context.
2. **Chat bootstrap** — operating instructions in `PASTE_THIS_INTO_YOUR_AI.md` for chat-only tools and non-repo workflows.
3. **Optional local scanner** — `tools/checkyourself.py` detects your stack and obvious issues with zero tokens.
4. **Optional dashboard** — a human-readable HTML/CSS view generated only when requested.
5. **Advanced capability stack** — deeper production-hardening workflows in `90_ADVANCED/`.

Use the simplest layer that gets you a useful answer.

## Success criteria

A stranger should be able to clone the repo, point their AI assistant at it, and get value in under five minutes.

## Recommended first action

Point your AI assistant at [`../CONTEXT.md`](../CONTEXT.md). For chat-only tools, use the bootstrap in [`../PASTE_THIS_INTO_YOUR_AI.md`](../PASTE_THIS_INTO_YOUR_AI.md).

## Important

The diagnostic produces a complete findings register and backlog. The first approval batch is only the first safe batch of remediation.
