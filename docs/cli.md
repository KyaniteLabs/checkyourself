# Optional local CLI: `tools/checkyourself.py`

CheckYourself is primarily a model-agnostic system you load as an AI assistant's
operating context. This CLI is **optional** — a deterministic head start that
does the cheap discovery locally so your AI spends its budget on judgment, not
grep. It uses only the Python standard library, sends nothing over the network,
and never prints secret values.

## What it does

- Detects the stack: manifests, frameworks, ORM/database, auth, payments,
  AI/RAG dependencies, tests, and CI.
- Flags obvious deterministic risks and ranks them P0–P3:
  - **P0** — possible hardcoded secrets / high-confidence credential shapes.
  - **P0** — a real `.env` that is not gitignored (possible committed secret).
  - **P1** — env vars used but no `.env.example`; no automated tests; payments
    present with no tests.
  - **P2** — no CI pipeline; a local `.env` present (verify it is untracked).
- Writes a pre-filled context Markdown file for your assistant.
- Optionally writes a machine-readable JSON summary.
- Returns a non-zero exit code under `--ci` when a P0 is found, so it can act as
  a lightweight CI gate.

It is **not** a replacement for the full AI-driven diagnostic. It is the scaffold
the diagnostic builds on — the AI still sweeps the entire production surface,
explains and ranks every finding, and produces the remediation backlog and
learning plan.

## Usage

```bash
# Scan a project and write CHECKYOURSELF_PROJECT_CONTEXT.generated.md
python3 tools/checkyourself.py /path/to/your/project

# Also emit a JSON summary
python3 tools/checkyourself.py /path/to/your/project --json

# Print machine-readable JSON to stdout
python3 tools/checkyourself.py /path/to/your/project --format json --no-write

# Print findings only, write nothing
python3 tools/checkyourself.py . --no-write

# Use as a CI gate (exit 1 if any P0)
python3 tools/checkyourself.py . --ci
```

### Options

| Flag | Meaning |
| --- | --- |
| `project` | Project root to scan (default `.`). |
| `--out PATH` | Markdown context output path (default `CHECKYOURSELF_PROJECT_CONTEXT.generated.md`). |
| `--json [PATH]` | Also write a JSON summary (default `CHECKYOURSELF_SCAN.generated.json`). Use `--json -` for stdout. |
| `--format text|json` | Console output format. Use `json` for machine-readable stdout. |
| `--ci` | Exit non-zero if any P0 finding is detected. |
| `--no-write` | Print the summary only; write no files. |
| `--quiet` | Suppress the console summary. |

## Handing the output to your AI

Give the generated `CHECKYOURSELF_PROJECT_CONTEXT.generated.md` to your assistant
along with the CheckYourself folder (or the bootstrap in
[`../PASTE_THIS_INTO_YOUR_AI.md`](../PASTE_THIS_INTO_YOUR_AI.md)) and ask it to run
the full diagnostic. The deterministic findings become confirmed evidence the AI
builds on.

Generated files match the gitignored `CHECKYOURSELF_*.generated.*` patterns, so
they stay out of commits by default.
