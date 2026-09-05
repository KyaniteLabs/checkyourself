# Cursor / Windsurf Adapter

Start with [`native-cli-mcp.md`](native-cli-mcp.md); this file only adds
editor-panel and workspace-context steps.

1. Put the `checkyourself/` folder inside the repo.
2. Open the chat/agent panel.
3. Ask:

```text
Use the checkyourself folder as context. Start with read-only diagnostic mode. Do not edit files until I approve a specific fix. Generate the learning plan after the report.
```

4. When approving a fix, ask for a small diff and verification.
