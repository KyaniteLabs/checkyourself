# CheckYourself candidate

CheckYourself re-derives completion claims and labels each CONFIRMED, REFUTED or UNVERIFIABLE. This candidate includes the verification skill, the standard-library Python CLI, schemas and staged methodology resources from b223e01. Its 11-tool stdio MCP server is launched with `python3` and the bundled tools/checkyourself.py. Python 3.10+ is required; pytest is only a test-suite dependency.

The server stays local: no uploads, network service or telemetry is added. CHECKYOURSELF_SCAN_ROOT is deliberately unset in the package; the boundary defaults to the process working directory. Start your host in the user-approved project directory, or deliberately set that variable to the approved scan root in your own host configuration. Never set it to the filesystem root as a convenience. Scans and scoring stay read-only by default. User-authorized challenge execution and report writes are separate actions and can create local evidence files.

The deep-lane setup resolves the bundled CLI relative to the installed skill and quotes paths. It asks you to begin in the directory containing SKILL.md, then scan an explicit project path. Files do not leave the machine through this server; results returned to an AI host are visible to that host, so select approved projects and avoid confidential output.

Local MCP loads in Claude Code and local Cowork sessions. Claude chat ignores local stdio entries. Validate with `claude plugin validate ./checkyourself-claude` and exercise read-only scanning in an installed host before public submission. This package is prepared, not installed or submitted.
