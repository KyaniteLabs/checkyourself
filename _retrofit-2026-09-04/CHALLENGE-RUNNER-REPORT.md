# Challenge Runner Report

## Outcome

The verifier-owned challenge runner is implemented and verified without a
commit or push. Caller-issued evidence remains available for compatibility but
is explicitly `UNVERIFIED`; only a successful `EXECUTED` receipt can satisfy a
coverage `Pass`.

## 1. Committed challenge definitions

Evidence:

- `.checkyourself/challenges.json` is the committed configuration.
- `schemas/challenges.schema.json` validates argv-list commands, project-root
  working directories, positive timeouts, exit/JSON/regex assertions, and
  `text`/`json` output kinds.
- The live repository matrix contains 20 surfaces and 10 scored categories.
  The config covers all 20 surface IDs; S11 has a working pytest default and
  the other surfaces are explicitly marked `requires_explicit_config`.
- `python3 tools/checkyourself.py validate --kind challenges .checkyourself/challenges.json --format json`
  returned `valid: true`.

An invalid command override is not repaired with a fallback. The runner emits
a verifier-observed `FAIL` receipt with an empty argv and an open challenge
finding, so a caller cannot weaken the execution requirement by deleting or
stringifying a command.

## 2. Verifier-owned execution

`challenge [--surface S]` loads committed definitions, invokes argv with
`subprocess.run(..., shell=False)`, enforces `timeout_s`, and captures both
stdout and stderr to `.checkyourself/challenge-runs/<surface>.capture.json`.
The receipt records only verifier observations: `surface_id`, argv `command`,
`exit_code`, capture path and SHA-256 digest, current project tree hash,
timestamp, timeout state, status, and challenge-definition digest. It contains
no caller-authored `claim`, `result`, `origin`, or `source_state` fields.

Receipt re-checks validate the receipt binding hash, capture digest and JSON
capture structure, re-apply the committed assertions, compare the current
tree/config digests, and never rerun or trust a caller-provided result string.

## 3. Scoring integration

- `issue_receipt` now labels its compatibility output `receipt_class:
  UNVERIFIED`; coverage verification rejects it for full credit with the
  message `UNVERIFIED caller-issued receipt; run challenge to mint executed
  evidence`.
- Successful `EXECUTED` receipts resolve to their captured-output evidence and
  can satisfy a `Pass` row.
- A `FAIL` or timeout remains receipted, creates `CY-CHALLENGE-Sxx` as an open
  P1 coverage finding, increments the scored P1 count, and applies the P1 cap
  of 74. It is not ignored or converted into a crash.
- Surface identity is checked before acceptance; an S02 receipt cannot satisfy
  S05 even when both commands are configured in the same project.
- A changed source tree or challenge definition downgrades the stored receipt
  to unknown, preventing stale execution evidence from reaching high
  confidence.

## 4. Regression evidence

Added regression tests cover the requested escape routes:

- `test_caller_issued_receipt_is_explicitly_unverified` — hollow caller-authored
  substance cannot reach high confidence.
- `test_invalid_override_fails_closed_without_shell_execution` — a string
  command override fails closed and does not execute shell text.
- `test_challenge_output_assertions_and_surface_binding` — JSON/regex
  assertions run against verifier-captured output and S02 evidence is rejected
  for S05.
- `test_failing_challenge_is_scored_as_a_finding_and_cap` — failed execution
  produces a scored finding and the 74 cap.
- `test_timeout_is_bounded_and_receipted_as_fail` — timeout is bounded and
  produces a `FAIL` receipt.
- `test_executed_receipt_is_invalid_after_source_tree_change` — source revision
  binding rejects stale output.
- `test_executed_challenge_receipt_is_the_only_full_credit_class` — a real
  successful execution is accepted for its own surface and contains no caller
  result/origin fields.

## 5. Dogfood demonstration

Command run against this repository:

```text
python3 tools/checkyourself.py challenge --surface S11 --format json
```

Observed result:

- `complete: true`
- `challenge_status: PASS`
- `exit_code: 0`
- `source_revision: 6d27cde41ed00f102ff7cc8ffbd2552c748b20a4866015831c1375081d16072c`
- `captured_output: .checkyourself/challenge-runs/S11.capture.json`
- `captured_output_digest: 5b9e3ea20268ba88c60f060951d4b54d81da252b261a8cd975c289624fdd93ca`
- `receipt_sha256: ca34ea4f04a7808ae7ec68949910861f47a746afb016a68f5dd02e073c324c66`
- `findings: []`

The capture and receipt files are local run artifacts under the ignored
`.checkyourself/challenge-runs/` directory. The report records their observed
paths and digests; it does not substitute for the receipt itself.

## 6. Required verification

- `python3 -m pytest tests/ -q` — `135 passed, 88 subtests passed`.
- `python3 tools/validate_public.py .` — `OK: public CheckYourself validation passed`.
- Challenge configuration schema validation — `valid: true`.
- Challenge result schema validation — `valid: true`.
- `git diff --check` — clean.
- Git state — changes remain uncommitted on the worker branch; no push was
  performed.

## IMPROVEMENTS

- Expand project-specific challenge templates beyond S11. This matters because
  the generic runner can execute only the self-test surface without inventing
  proof for product-specific auth, data, deploy, and privacy behavior. Add
  documented adapters for common stacks, each requiring explicit owner review.
- Add a read-only MCP `challenge` tool with an explicit output-artifact
  contract. This matters because the native CLI and MCP surface currently have
  different access to verifier-owned execution. Expose the same runner behind
  a clearly non-networked, local-root-bounded tool.
- Add immutable run IDs and a small manifest per challenge wave. This matters
  because the current per-surface capture and receipt filenames are replaced
  on rerun. Store timestamped runs with a latest pointer so historical proof is
  recoverable without changing scoring semantics.
