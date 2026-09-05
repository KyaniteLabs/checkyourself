# STREAK6 Grok independent review — HEAD 091b343

Branch: `retrofit/2026-09-04`
HEAD: `091b343a41f3516decabd69d3ab9fdc10c412f7e`
Reviewer: grok-4.6 (read-only in-memory probes)

## Acceptance chain

- `python3 -m pytest tests/ -q` → **123 passed, 88 subtests passed**
- `python3 tools/validate_public.py .` → **OK**

Round-5 regressions still hold (29/low and 82/low).

## Round-5 exploits re-run (must fail closed)

| Probe | Result | 100/high? |
|---|---|---|
| Authentic-but-irrelevant **caller-authored** receipt on every Pass surface | score **29**, conf **low**, caps 84+90 | no |
| Coverage Finding linked only to **resolved** finding ID | score **82**, conf **low**, caps 84+90, `CY-COVERAGE-S07` scored | no |

## New laundering variants

| Probe | Result | 100/high? |
|---|---|---|
| Same receipt object copied across surfaces (reuse) | **29/low** | no (fail closed) |
| Delegation reuse of a Pass receipt | **29/low** | no (fail closed) |
| Tamper `issued_at` without rehash | **29/low** | no (fail closed) |
| Empty `finding_ids` on Finding rows (C1/C2/C3) | **58/low** | no (fail closed) |
| **Per-surface `issue_receipt()` of one irrelevant README** | **100/high**, no caps | **YES** |
| **Copy receipt, change `surface_id`, recompute `receipt_sha256`** | **100/high**, no caps | **YES** |

## Finding

Receipts are cryptographic and surface-bound, but **not semantically bound**. Any existing file can be issued as a verifier receipt for every canonical surface. Rebinding `surface_id` and recomputing the digest is equivalent to legitimate re-issuance: `_verify_receipts` only checks issuer, hash coverage, path hash, and surface/claim match. It does not check that the artifact is relevant to the surface.

This is the remaining round-5 hole after provenance/issuer closure: **authentic file + verifier-issued receipts + unique binding hashes = launch-ready 100/high**.

## Verdict

FULLY-GREEN: no

## IMPROVEMENTS

1. **Bind receipt claims to surface semantics.** Why: a README hash currently Passes auth, secrets, and rollback. Fix: require `command`/`claim` to name the surface id and reject one content-hash reused across more than N surfaces even with distinct `receipt_sha256`.
2. **Treat rebind-as-new-receipt as reuse of `sha256`+`reference`.** Why: probe 7 got 100/high by only changing `surface_id` then rehashing. Fix: track used content hashes (or reference+sha256) in `used_receipt_ids`, not only `receipt_sha256`.
3. **Add a regression test for “one artifact, 20 issued receipts”.** Why: round-5 tests only cover caller-authored provenance, so this 100/high path is unguarded. Fix: assert score ≤ 84 / not high when every surface cites the same file.
