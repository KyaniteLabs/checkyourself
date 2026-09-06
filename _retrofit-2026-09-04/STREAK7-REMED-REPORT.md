# Streak 7 remediation report — per-surface artifact registry

Date: 2026-09-05
Worker: `w-16dd-cy-streak7-remed`
Scope: close Grok's registry-gap exploit for verifier receipts. No installs,
network calls, commits, or pushes.

## Result

The receipt subject is now both cryptographically bound and semantically
registered. The default registry covers every `S01`–`S20` coverage-matrix
surface, including all 10 scored categories. Each contract requires:

- an in-root path under `coverage/verification/<surface-id>/`;
- a `*.json` artifact pattern;
- a JSON object with `kind: surface-verification-record`;
- matching `surface_id`, plus non-empty `source_revision`, `command`, and
  `result` fields.

`.checkyourself.json` can explicitly override individual surface roots,
patterns, expected kind, and required fields. Invalid overrides fail closed.
The registry check runs at both `issue_receipt` and coverage verification, so
an unregistered or cross-surface artifact becomes `Unknown` and remains capped.
The same contract applies to `delegation_receipts`.

## Mandatory regressions

| Probe | Observed result | Verdict |
| --- | --- | --- |
| C — 20 distinct existing-but-unregistered files, one per Pass surface | `29/100`, low confidence, `coverage_complete=false`, caps `84` and `90` | Fail closed; not high/100 |
| F — 20 distinct existing-but-unregistered files, one per NotApplicable/delegation surface | `29/100`, low confidence, `coverage_complete=false`, caps `84` and `90` | Fail closed; not high/100 |

Both probes also assert that `issue_receipt` rejects each unregistered file at
issuance. The tests use forged-but-structurally-valid receipt objects for the
score path to prove verification independently rejects the subjects.

## Additional coverage

- Explicit registry override accepts a valid custom S11 path and rejects a
  record with the wrong content shape.
- Cross-surface rebinding remains rejected because the artifact path and record
  identity belong to the original surface.
- Existing valid receipt and NotApplicable fixtures now use the shipped record
  contract rather than arbitrary files.

## Acceptance evidence

- `python3 -m pytest tests/ -q` — **128 passed, 88 subtests passed**.
- `python3 tools/validate_public.py .` — **OK: public CheckYourself validation passed**.
- `python3 -m py_compile tools/checkyourself.py` — **passed**.
- `git diff --check` — **passed**.
- Worktree contains only the four intended modified/created artifact families;
  no commit or push was performed.

## Changed files

- `tools/checkyourself.py` — default registry, config validation/overrides,
  issuance and verification enforcement, capability descriptions.
- `tests/test_checkyourself_cli.py` — contract fixtures, override test, and C/F
  fail-closed regressions.
- `docs/cli.md` — artifact record and override contract.
- `docs/mcp.md` — registered-artifact receipt boundary.
- `_retrofit-2026-09-04/STREAK7-REMED-REPORT.md` — this report.

## IMPROVEMENTS

1. **Add a first-class verification-record emitter.** WHY: tests and callers
   currently hand-author the small JSON proof record before issuing a receipt.
   FIX: add a dependency-free command that captures the command result and
   writes the registered record shape atomically.
2. **Support registry overrides in YAML as well as JSON.** WHY: this checkout's
   existing `.checkyourself.yml` parser is intentionally suppression-only, so
   registry overrides must use a second config format. FIX: extend the minimal
   parser with bounded nested registry mappings, or document one canonical
   config format and reject silently ignored registry keys.
