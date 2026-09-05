# ROLE: LUNA FIX TEAM — STREAK-2 REMEDIATION (checkyourself; DSV4 round-2 findings)
DSV4 streak-2 verdict: FULLY-GREEN no. Findings to close as REAL tests (a production-readiness product must prove what it preaches):
1. NEGATIVE-PATH TESTS: NaN/Inf safety across scoring/weight paths; malformed JSON inputs at every CLI subcommand; unicode/empty/huge-string edges in scan+score+backlog+next+diff.
2. CRASH-INJECTION: simulated partial/corrupted state files (coverage mid-write, receipts truncated) — scanner must fail closed, never silently recover wrong.
3. ROUND-TRIP REPORT CONTRACT: score->report->schema-validate round-trip test (generated report validates against the report schema, and invalid mutations of it are rejected).
4. CRASH-RECOVERY WRITES: interrupted-write semantics (the zero-byte cure proven under simulated interruption).
5. LINE-ENDING DIFF TRUTHFULNESS: diff --ci with CRLF/LF/mixed fixtures behaves deterministically and honestly.
Acceptance: python3 -m pytest tests/ -q ALL green incl. new tests; validate_public green. Write _retrofit-2026-09-04/STREAK2-REMED-REPORT.md. GIT: none. No installs/network.
