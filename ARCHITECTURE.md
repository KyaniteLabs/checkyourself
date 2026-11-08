# CheckYourself architecture

## Parts / flow

`CONTEXT.md` routes agents through purpose, diagnostics, approval-gated fixes, learning and optional presentation. Markdown reports remain the workflow record; the Python tool does not replace full engineering judgment.

`tools/checkyourself.py` is a compatibility launcher into `tools/checkyourself/`; `cli.py` parses verbs, `scan/scanning/detectors` inspect local files, `coverage/scoring` fold evidence and severity caps, `planning` ranks work, and `validation/report` check/render artifacts. MCP and npm wrappers reach the same implementation. Schemas define machine output contracts; staged context/templates define assistant behavior.

```text
project source -> bounded scan -> findings + stack/limits
committed challenges -> argv subprocess + assertions -> output/receipt bindings
findings + coverage + receipt rechecks -> capped score -> report/backlog/next
```

[challenge_run.py](tools/checkyourself/challenge_run.py) validates project-relative working directories, hashes the source tree and captures command execution; [receipts.py](tools/checkyourself/receipts.py) resolves registered artifacts within evidence roots and verifies bindings; [scoring.py](tools/checkyourself/scoring.py) normalizes findings and applies coverage/severity constraints. See [CLI dispatch](tools/checkyourself/cli.py): stdout-only scanning differs from explicitly requested output files, starter-file initialization and challenge receipts.

## Risk / failure boundaries

- A challenge is executable project-supplied code, not inert evidence. Argv/no-shell and timeouts do not sandbox filesystem/network access. Executed-receipt verification may rerun commands at score time. Audit definitions before either path.
- Local HMAC/hash bindings detect some edits, not independent operator identity or external custody. Stale source/config/output, weak assertions and caller-issued receipts must not silently earn executed credit.
- Scanner truncation, unreadable/oversized files and heuristics affect coverage; absence of a finding is not evidence a surface works. Backlog ordering is not dependency/blast-radius/safety analysis.
- Diagnostic outputs can expose project structure and findings. Keep private creator/local-agent state outside public releases. Optional dashboards should be generated only on explicit request, not treated as an independent UI/data source.

## Docs proof

Purpose/context/rules and actual launcher/CLI/challenge/receipt/scoring implementation inspected. `validate_public.py .` passed; CLI describe and `scan . --no-write --format json` succeeded (one P2, no truncation). No deletion-cleanup tests, challenge execution, score rerun, dashboard generation, network model or user project mutation. Session receipts are separate from independent acceptance; revert these docs for rollback.
