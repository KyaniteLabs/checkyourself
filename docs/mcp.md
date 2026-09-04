# MCP Wrapper

CheckYourself ships a local stdio MCP server:

```bash
python3 tools/checkyourself.py mcp
```

It is intentionally thin. The MCP server does not implement separate audit
logic. It calls the same functions as the CLI, returns the same schema-backed
JSON, and keeps the product local-first.

Use the canonical [`native CLI/MCP adapter`](../06_ADAPTERS/native-cli-mcp.md)
for host discovery, scan-root setup, and write-boundary guidance.

## Why Local Stdio

CheckYourself inspects local project folders. That makes local stdio the right
MCP transport for the public repo:

- no hosted account;
- no file upload;
- no API key;
- no remote storage;
- no extra runtime dependency;
- no second implementation.

The current MCP spec defines stdio messages as newline-delimited JSON-RPC over
stdin/stdout. The server writes logs only to stderr and writes only valid MCP
messages to stdout. See the official MCP transport and tools specs:
[`Transports`](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
and [`Tools`](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).

## Tools Exposed

| MCP tool | Same CLI behavior |
| --- | --- |
| `describe` | `checkyourself describe --format json` |
| `scan` | `checkyourself scan PROJECT [--deep] --format json --no-write` |
| `coverage_emit` | `checkyourself coverage --emit --format json` |
| `coverage_check` | `checkyourself coverage --check FILE` logic, with an inline object |
| `score` | `checkyourself score --findings FILE [--coverage FILE]` logic, with inline objects and no history write |
| `backlog` | `checkyourself backlog --findings FILE` logic |
| `next` | `checkyourself next --findings FILE` logic |
| `diff` | compare two findings objects (`old`, `new`); returns added/resolved/regressed findings and a `regression` boolean flag |
| `validate` | `checkyourself validate --kind KIND FILE` logic, with an inline object |
| `schema` | `checkyourself schema NAME` |

## Example Client Config

Use this shape in MCP clients that accept a local stdio server command:

```json
{
  "mcpServers": {
    "checkyourself": {
      "command": "python3",
      "args": [
        "/absolute/path/to/checkyourself/tools/checkyourself.py",
        "mcp"
      ]
    }
  }
}
```

## Expected Agent Flow

1. Call `describe`.
2. Call `scan` on the project folder. Use `deep: true` when the agent needs CI/supply-chain validation evidence.
3. Run the full CheckYourself diagnostic in the coding agent.
4. Fill coverage evidence.
5. Call `coverage_check`.
6. Call `score`. Without coverage, treat the result as a low-confidence estimate and read `manual_evidence_needed`.
7. Call `backlog`.
8. Call `next`.
9. Ask before making any fix.

## Security Boundaries

MCP scans are confined to the directory set by the `CHECKYOURSELF_SCAN_ROOT` environment variable. If the variable is not set, the server defaults to its own working directory at startup. Scan paths that resolve outside that root are rejected with an error before any file access occurs.

Unknown tool arguments are also rejected rather than silently ignored. MCP host operators should set `CHECKYOURSELF_SCAN_ROOT` to the narrowest directory the agent legitimately needs to inspect, and should treat any rejection as a signal that the host is sending unexpected input.

## What This Is Not

This is not a hosted API. It is not an MCP app with widgets. It is not a second
product surface with its own scoring rules.

Useful side-eye: if the MCP and CLI disagree, the product has two engines. That
is how launch tools become launch problems.
