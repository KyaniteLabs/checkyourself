# Claude / Project Knowledge Adapter

Start with [`native-cli-mcp.md`](native-cli-mcp.md); this file only adds Claude
Project Knowledge loading steps.

This adapter is provided for users who use Claude or Claude-like project knowledge systems. CheckYourself is not Claude-specific.

## Path

1. Add this folder to the project knowledge or repo.
2. Point the file-aware tool at `CONTEXT.md` first — this is the canonical router that loads the right stage context.
3. Ask the assistant to read `AGENTS.md`, `rules.md`, and `PASTE_THIS_INTO_YOUR_AI.md`.
4. Run the diagnostic.
5. Approve fixes one at a time.
