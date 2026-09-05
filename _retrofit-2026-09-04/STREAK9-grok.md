# STREAK 9 — Grok independent review (post challenge-runner)

HEAD: `55075e8` (`retrofit/2026-09-04`) — challenge runner commit.
Method: read-only; pytest; `validate_public.py`; in-memory temp trees only.

## Acceptance chain

- `python3 -m pytest tests/ -q` → **135 passed, 88 subtests passed**
- `python3 tools/validate_public.py .` → **OK: public CheckYourself validation passed**

## Probe results (in-memory)

| Probe | Result | Score / status | Verdict |
| --- | --- | --- | --- |
| A — 20 hollow registered JSON + `issue_receipt` | 20/20 issued as `UNVERIFIED` | **29 / low / complete=false / caps 84+90** | fail closed (round-8 hollow closed) |
| B — override `required_fields` reduced to identity keys | 20/20 issued; coverage still rejects caller class | **29 / low / 84+90** | fail closed (override weakening no longer scores) |
| C — widened `path_roots` + per-surface rewritten JSON | 20/20 issued; still UNVERIFIED class | **29 / low / 84+90** | fail closed |
| D — real EXECUTED S02 receipt applied to S05 | surface binding reject | C2 **Unknown**; 29 / low | fail closed |
| E0 — forged EXECUTED using **raw** (unmerged) definition digest | verify rejects digest | **29 / low**; all cats Unknown | fail closed (wrong digest) |
| E1 — forged EXECUTED using **merged** `load_challenge_config` definition, matching capture digest, tree hash, binding hash; **no `challenge_from_root` / no subprocess** | 20/20 `_verify_executed_receipt` OK | **100 / high / coverage_complete=true / no caps** | **escape** |
| F — real run then substitute `receipt.command` (re-hash binding) | command ≠ committed definition | C5 **Unknown** | fail closed |
| G — real run then mutate committed `challenges.json` | config digest mismatch | C5 **Unknown** | fail closed |

## Findings

1. **Caller-issued / hollow / override-weaken / cross-surface paths no longer mint 100.** Round-8 class is dead for `issue_receipt` because `_verify_receipts` rejects anything that is not `receipt_type == EXECUTED`.
2. **On-disk EXECUTED JSON is reconstructible.** Challenge-runs are excluded from `current_tree_hash`. `_verify_executed_receipt` re-checks hashes, tree, config digest, argv match, and re-applies assertions against the **stored capture**. It does not prove `subprocess.run` happened. A hand-written capture (`stdout` that satisfies `exit_zero`) plus a receipt whose `receipt_sha256` is `_executed_receipt_binding_digest` of those fields scores **100/high** for all ten categories.
3. **Naive forgeries fail; informed forgeries pass.** Using the raw override object for `challenge_config_digest` fails because verification hashes the **merged** default+override definition. That is a speed bump, not a trust boundary.

## False-green hunt

Shipped tests cover UNVERIFIED caller receipts, invalid string commands, cross-surface S02→S05, fail/timeout findings, and stale tree/config. They do **not** assert that a well-formed EXECUTED receipt must have been minted by this process’s runner. Happy-path credit is “shape + digests + assertions on stored stdout.”

FULLY-GREEN: no
