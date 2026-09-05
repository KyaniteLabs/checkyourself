# STREAK 8 — Grok independent review

HEAD: `c17a0475d1e00568018b67b59d87891984fd3c2a` (`retrofit/2026-09-04`)
Method: read-only; pytest; `validate_public.py`; in-memory probes (temp trees only).

## Acceptance chain

- `python3 -m pytest tests/ -q` → **128 passed, 88 subtests passed**
- `python3 tools/validate_public.py .` → **OK**

## Probe results (in-memory)

| Probe | Issuance | Score | Verdict |
| --- | --- | --- | --- |
| C — 20 distinct unregistered Pass files | 20/20 `CliError` unregistered | **29 / low / coverage_complete=false / caps 84+90** | fail closed (round-7 RED closed) |
| F — 20 distinct unregistered N/A files | 20/20 reject | **29 / low / false / 84+90** | fail closed |
| Hollow contract JSON (registered path, fields present but placeholder `n/a` / `true` / `ok`) | **20/20 issue_receipt succeeds** | **100 / high / coverage_complete=true / no caps** | **escape** |
| Hollow missing `result` | 20/20 reject | 29 / low / 84+90 | fail closed |
| Cross-surface `../S01/proof.json` | 1 ok (S01 itself after resolve), 19 reject | 29 / low / 84+90 | fail closed for foreign surfaces |
| Override: `required_fields` reduced to `surface_id`+`kind` (accepted, `registry_error=None`) then `{kind,surface_id}` only | 20/20 issue | **100 / high** | **override weakening accepted** |
| Override: `path_roots=["coverage/verification"]` — S02 receipt on `coverage/verification/S01/proof.json` | **issued** | shared-root 20/20 → **100 / high** | **cross-surface via widened root** |
| Invalid overrides (`..` in roots, unknown `S99`, empty `required_fields`) | validator error | n/a | fail closed as specified |

## Findings

1. **Registry presence ≠ verification quality.** Default registry only requires non-empty JSON strings for `source_revision`, `command`, `result`. Placeholder records at the registered path mint real verifier receipts and unlock **100/high**. Round-7 uniqueness gap is closed; **relevance/substance is still unenforced**.
2. **Explicit registry overrides can weaken, not only relocate, the contract.** Dropping `required_fields` to identity keys is valid config. Widening `path_roots` to the parent verification tree lets surface S02 issue against S01’s file if JSON `surface_id` is rewritten. Invalid overrides fail closed; **abusive-but-well-formed overrides do not**.
3. **Path `..` is resolved** (`Path.resolve` in `_resolve_evidence_reference`), then matched on the canonical relative path. Foreign-surface `../` does not mint 100.

## False-green hunt

Shipped tests cover unregistered C/F and invalid override syntax. They do **not** assert that contract-shaped hollow records fail to reach high/100. Happy-path fixture records are the same shape as the hollow probe (`kind` + five strings).

FULLY-GREEN: no
