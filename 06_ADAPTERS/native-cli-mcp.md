# Native CLI and MCP Adapter

Use this as the canonical adapter when the host can run a local command or
connect a local stdio MCP server. Provider-specific files add only host setup
details and do not replace these boundaries.

## Discover the interface

Run the pure discovery command first:

```bash
python3 tools/checkyourself.py describe --format json
```

The manifest lists the CLI commands, coverage surfaces, scoring caps, schemas,
exit codes, and MCP capability. Validate the captured manifest when a machine
receipt is needed:

```bash
python3 tools/checkyourself.py validate --kind capabilities capabilities.json
```

## Read-only CLI path

Use the explicit no-write scan for the first receipt:

```bash
python3 tools/checkyourself.py scan /path/to/project --deep --format json --no-write
```

Then use the same CLI engine for coverage, scoring, backlog, next batch, diff,
and artifact validation. For stdout-only workflows, use `--format json` and
`--no-history` for `score`; do not use a path-writing option unless the user
explicitly requested an artifact.

The write boundary is explicit:

- `scan --no-write`, `describe`, `schema`, `validate`, `backlog`, `next`, and
  `diff` are the default inspection/receipt path;
- `coverage --emit` without `--format json` writes its named skeleton, so use
  stdout mode for inspection and write it only when requested;
- `score --no-history` avoids score-history writes;
- `--out`, `--json PATH`, `init`, and an explicit history path write files and
  require a user-approved output target;
- code, configuration, production systems, secret rotation, and external
  communication remain outside the adapter's authority and require explicit
  approval.

## Native MCP path

Start the local server with the narrowest scan root:

```bash
CHECKYOURSELF_SCAN_ROOT=/path/to/project python3 tools/checkyourself.py mcp
```

The client should call `initialize`, `tools/list`, and then `describe` before
using `scan`, `coverage_emit`, `coverage_check`, `score`, `backlog`, `next`,
`diff`, `validate`, or `schema`. MCP is a thin wrapper over the same CLI
functions. It does not upload files, use an API key, or write score history.
Requests outside `CHECKYOURSELF_SCAN_ROOT` and unknown arguments are rejected.

## Approval boundary

The adapter can discover, inspect, score, and prepare a remediation proposal.
It must stop before code/config edits, `init` writes, persistent report output,
secret changes, or production actions until the user approves the named change
and output target.
