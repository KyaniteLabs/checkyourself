# CheckYourself

A local-first completion-evidence workflow for people building apps with AI assistants. Its core loop is diagnose read-only, record observed/inferred/untested behavior, review the complete findings/backlog, approve small fixes, verify, rescore and learn. A score is not certification or independent evidence custody.

## Existing surfaces

- A staged Markdown operating context (`CONTEXT.md`, diagnostic/fix/learning stages), 19-capability hardening guidance, report/risk templates and an optional dashboard template—not an autonomous hosted auditor.
- Stdlib Python CLI and stdio MCP wrapper; optional npm launcher invokes the same Python implementation. Actual `describe` emits 15 command entries, including aliases and coverage variants, not 15 MCP tools.
- Deterministic stack/risk scanning, 20-surface coverage, 10-category bounded scoring, backlog/next-batch ordering, artifact schemas, diff and report validation.
- Verifier-executed committed challenges, captured output, source/config binding, local integrity receipts and score-time rechecks; caller-issued evidence remains distinct from executed evidence.
- Bundled schemas, sample reports, fixtures and methodology—not a benchmark proving arbitrary applications production-safe. Full assistant judgments, safety/dependency analysis and approved fixes remain human/agent work.

## Verification and limits

Public repository validation passed; actual read-only scan completed without truncation and reported one P2 finding. Help/describe/scan outputs were captured. No arbitrary challenge, score-time challenge rerun, remediation, dashboard generation or production audit ran; no user-side operator recording establishes acceptance.

A project-local HMAC does not establish an independent issuer. Challenge commands can execute code and score-time verification can rerun them: read-only scanning is not a sandbox guarantee for every verb. Review commands and scope before execution. See [ARCHITECTURE.md](ARCHITECTURE.md), [README.md](README.md) and [CONTEXT.md](CONTEXT.md).
