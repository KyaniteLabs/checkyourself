# 06 — Adapters

CheckYourself is model-agnostic. Use the adapter that matches your environment.

- [`native-cli-mcp.md`](native-cli-mcp.md) — canonical native CLI/MCP path, discovery, and write boundaries
- [`chatgpt.md`](chatgpt.md)
- [`claude-projects.md`](claude-projects.md)
- [`cursor-windsurf.md`](cursor-windsurf.md)
- [`replit-lovable-bolt.md`](replit-lovable-bolt.md)
- [`local-agents.md`](local-agents.md)

Start with `native-cli-mcp.md` whenever the host can run local commands or
connect a local stdio MCP server. The provider files are deltas for file upload,
project-context, or chat-panel behavior; they must not redefine the CLI/MCP
contract, its read-only defaults, or its approval boundary.

The core system is the folder and prompts, not a specific model provider.
