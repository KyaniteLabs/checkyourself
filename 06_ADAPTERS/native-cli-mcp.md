# Native CLI and MCP Adapter

Use when the host runs local commands or connects a local stdio MCP server;
provider files add setup only.

## Discover the interface

Run discovery first:

```bash
python3 tools/checkyourself.py describe --format json
```

The manifest lists commands, surfaces, caps, schemas, exit codes, and MCP
capability. Validate it for a machine receipt:

```bash
python3 tools/checkyourself.py validate --kind capabilities capabilities.json
```

## Read-only CLI path

Use the explicit no-write scan for the first receipt:

```bash
python3 tools/checkyourself.py scan /path/to/project --deep --format json --no-write
```

Use the same engine for coverage, scoring, backlog, next batch, diff, and
artifact validation. For stdout-only workflows, use `--format json` and
`--no-history` for `score`; write paths only for a user-requested artifact.

Write boundary:

- `scan --no-write`, `describe`, `schema`, `validate`, `backlog`, `next`, and
  `diff` are the default inspection path;
- `coverage --emit` without `--format json` writes its named skeleton, so use
  stdout mode for inspection; write only when requested;
- `score --no-history` avoids score-history writes;
- `--out`, `--json PATH`, `init`, and an explicit history path write files and
  require a user-approved target;
- code, configuration, production systems, secret rotation, and external
  communication remain outside adapter authority and require explicit approval.

## Native MCP path

Start with the narrowest scan root:

```bash
CHECKYOURSELF_SCAN_ROOT=/path/to/project python3 tools/checkyourself.py mcp
```

Call `initialize`, `tools/list`, then `describe` before `scan`,
`coverage_emit`, `coverage_check`, `score`, `backlog`, `next`, `diff`,
`validate`, or `schema`. MCP wraps the same CLI; it does not upload files, use
an API key, or write score history. Requests outside
`CHECKYOURSELF_SCAN_ROOT` and unknown arguments are rejected.

## Approval boundary

The adapter may discover, inspect, score, and prepare a remediation proposal.
Stop before edits, `init` writes, persistent output, secret changes, or
production actions until the user approves the named change/target.
