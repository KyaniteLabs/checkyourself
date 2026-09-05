# Streak 6 remediation report

Date: 2026-09-05
Scope: receipt subject binding and receipt rebinding fail-closed behavior

## Result

The two surviving Grok issuance variants now fail closed. A receipt carries a
`subject_digest` equal to the content hash of the verifier-captured artifact.
Issuance rejects an explicitly supplied digest that does not match that
artifact. Verification also requires the digest to match both the receipt's
content hash and the current artifact bytes.

Receipt binding hashes now cover `subject_digest`. Coverage verification tracks
the receipt binding hash, the subject digest, and the reference-plus-subject
identity in `used_receipt_ids`. Rebinding a copied receipt and recomputing its
binding therefore remains reuse, rather than becoming a new receipt.

## Mandatory regressions

| Probe | Observed result | Verdict |
| --- | --- | --- |
| One artifact, 20 issued receipts | **33/100, low confidence**; critical-evidence cap **84** applied | Fail closed; not high |
| Copy receipt, change `surface_id`, recompute `receipt_sha256` | **82/100, low confidence**; critical-evidence cap **84** applied | Fail closed; not high |

Focused tests pin both probes and the issuance mismatch path:

- `test_one_artifact_twenty_issued_receipts_fails_closed`
- `test_rebound_receipt_with_rehashed_binding_fails_closed`
- `test_receipt_subject_digest_must_match_registered_artifact`

## Acceptance receipts

- `python3 -m pytest tests/ -q` → **126 passed, 88 subtests passed**.
- `python3 tools/validate_public.py .` → **OK: public CheckYourself validation passed**.
- No git commit or push was performed.

## Changed surfaces

- `tools/checkyourself.py`: subject digest issuance, binding, semantic validation,
  duplicate-subject rejection across all 20 canonical surfaces, score folding,
  CLI/MCP plumbing, and capability descriptions.
- `schemas/receipt.schema.json` and `schemas/coverage.schema.json`: required
  `subject_digest` contract.
- `tests/test_checkyourself_cli.py`: receipt helper update and mandatory
  regressions.
- `docs/cli.md` and `docs/mcp.md`: receipt subject-binding contract.

## IMPROVEMENTS

1. Add a first-class verifier registry for surface-specific commands. The
   current patch binds the subject to the artifact supplied to the verifier;
   the remaining friction is that the generic receipt command does not itself
   execute or independently select the surface verification command. A future
   registry should map each surface to an approved verifier and emitted
   artifact before issuance.
2. Add a shared probe fixture module for adversarial receipt tests. The same
   receipt construction logic is currently repeated between production tests
   and external review probes, which makes probe drift harder to spot. A
   fixture API can generate valid receipts and mutation variants from one
   contract.
