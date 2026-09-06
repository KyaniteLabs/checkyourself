# CheckYourself dogfood defect retrofit

Date: 2026-09-04
Scope: CheckYourself CLI and scanner only
Git: no commit, no push, no installs, no network

## Result

Fixed all three dogfood defects and preserved fail-open behavior for real
secrets and unguarded sinks.

## Changes

1. Score/coverage pipeline readability
   - `score` validation errors now say: `fill coverage.json with evidence,
     then re-run score`.
   - Text `coverage --emit` output gives the same next action.
   - `docs/cli.md` documents the intentional skeleton-to-evidence handoff.

2. Failed JSON redirects
   - JSON-mode CLI errors now emit a valid JSON object on stdout:
     `{"error": "...", "code": 2}`.
   - This keeps `score --format json > file` parseable even when the emitted
     coverage skeleton is not yet valid for scoring. The command still exits
     non-zero and writes the human-readable error to stderr.

3. False-positive detector noise
   - Low-confidence secret assignments in docs, tests, fixtures, examples,
     audits, and snapshots are context-suppressed with structured reasons.
   - Detector regex/source strings and quoted guard guidance are suppressed.
   - Explicitly guarded eval calls are suppressed only when a nearby
     blocked-pattern check and safe/wrapped argument are present; isolated
     `page.evaluate` function reconstruction is also identified explicitly.
   - High-confidence credential shapes and unguarded application sinks remain
     findings.
   - Context suppressions are emitted in `context_suppressions` with `path`,
     `line`, `detector`, and `reason`; the total is in
     `context_suppression_count`.
   - Path-scoped user suppressions now filter evidence individually, so one
     reviewed doc match cannot suppress a real `.env` or runtime match in the
     same finding.
   - The minimal YAML parser now accepts the multiline `files:` list used by
     the liminal dogfood config.

## Verification

### Tests

`python3 -m unittest discover -s tests -p 'test_*.py'`
Result: 101 tests passed.

New regression coverage proves:

- the exact coverage handoff text;
- parseable JSON after a failed redirected score;
- multiline YAML path suppressions;
- evidence-level config suppression;
- docs/tests/detector/guarded-eval suppression;
- preservation of a real secret-like assignment and `eval(userInput)`.

### Self-repo acceptance pipeline

All commands returned exit code 0 and emitted the listed schema:

| Command | Schema/result |
|---|---|
| `describe --format json` | `checkyourself-capabilities/1` |
| `scan . --format json --no-write` | `checkyourself-scan/1`; 244 files; P0/P1/P2/P3 = 0/0/0/0 |
| `coverage --emit --format json` + filled artifact | `checkyourself-coverage/1` |
| `coverage --check ... --format json` | `checkyourself-coverage-check/1`; complete = true |
| `score ... --coverage ... --no-history --format json` | `checkyourself-score/1`; score/raw = 29/29; low-confidence by design for Unknown quick-sweep evidence |
| `backlog --findings ... --format json` | `checkyourself-backlog/1`; 0 items |
| `next --findings ... --format json` | `checkyourself-next-batch/1`; no IDs |
| `diff --old ... --new ... --format json` | `checkyourself-diff/1`; regression = false; added/resolved/unchanged = 0/0/0 |

### Liminal spot-check

Command: `python3 tools/checkyourself.py scan
/path/to/your/project --format json --no-write`

- Exit code: 0; 4,954 files scanned.
- `config_error`: null; the reviewed multiline suppression config is now
  usable.
- Remaining open findings: `CY-ENV-002` and `CY-SECRET-002`, both P2.
- `CY-SECRET-002` retains 7 runtime/local-env evidence items and records 43
  reviewed path-scoped matches under `suppressed_evidence`; the real `.env`
  evidence remains visible.
- No `CY-CODE-001` remains from the guarded/detector eval matches.
- 156 context matches were suppressed; 100 detailed entries are emitted in
  the bounded receipt, with reason counts: review-context paths 88, detector
  source strings 7, guarded eval 2, quoted detector/guard guidance 2, and
  isolated `page.evaluate` reconstruction 1.

## Remaining concern

The liminal P2 findings are expected and intentionally unresolved: the local
`.env` still needs historical exposure verification, and seven runtime/local
secret-like assignments still need human review. This retrofit does not mark
those risks accepted or fixed.

## IMPROVEMENTS

1. Emit paginated or file-backed context-suppression receipts. The liminal
   spot-check hit the 100-entry detail bound while the exact count was 156;
   provide an explicit export path so no reason is hidden by the bound.
2. Replace the minimal YAML parser with a documented supported subset or a
   standard-library-compatible parser strategy. The multiline `files:` bug
   made a valid reviewed config look invalid and weakened the scanner until
   this retrofit.
3. Add a dedicated `coverage fill`/authoring helper. The new message explains
   the handoff, but agents still must manually transform 20 null statuses into
   evidence-backed rows before scoring.
