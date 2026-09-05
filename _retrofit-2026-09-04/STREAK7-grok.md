# STREAK 7 — Grok independent review

HEAD: `efba94f5c36cbdeeef495cc1b93f545664f7208e` (`retrofit/2026-09-04`)
Read-only. No repo writes except this report.

## Acceptance chain

- `python3 -m pytest tests/ -q` → **126 passed, 88 subtests passed**
- `python3 tools/validate_public.py .` → **OK**

Round-6 regressions still fail closed. Unique-file issuance does not.

## Round-6 probes (re-run)

| Probe | Result | 100/high? |
|---|---|---|
| A. Per-surface `issue_receipt` of one README | **29/low**, cap 84+90 | no |
| B. Copy + change `surface_id` + rehash | **29/low**, cap 84+90 | no |

Brief cited 33/low for A; this HEAD scores **29/low**. Same fail-closed outcome.

## New issuance/binding variants (in-memory)

| Probe | Result | 100/high? |
|---|---|---|
| D. Issue with mismatched `subject_digest` | **CliError** at issuance | n/a (fail closed) |
| E. Case-flip `subject_digest`/`sha256` + rebind | **29/low** | no |
| H. Path-alias `README.md` vs `./README.md` after S01 | reuse/unknown path; **29/low** | no |
| I. Tamper `surface_id` after binding hash | binding mismatch → Unknown; **29/low** | no |
| **C. Unique existing file per surface (Pass)** | **100/high**, caps=[], complete=True | **YES** |
| **F. Unique file per surface (NotApplicable)** | **100/high** | **YES** |

### Finding (SEV-1): subject binding is uniqueness, not relevance

`issue_receipt` hashes whatever path the caller names. `subject_digest` must equal that file's bytes. Reuse tracking blocks **the same digest** across surfaces. It does not bind a surface to a **registered** verification artifact for that surface.

Twenty distinct, irrelevant markdown files (CONTEXT/README templates under `00_START_HERE` … `03_GUIDED_FIX_MODE`) issued once each with matching `surface_id`/`claim`/`evidence_reviewed` yield:

- score **100**, confidence **high**, `coverage_complete` true, no caps
- all score categories awarded full weight (`C1` 18 … `C10` 6)

Same pattern with `NotApplicable` + `delegation_receipts`.

There is no per-surface artifact registry. "Registered verification artifact" in the remed report means "the file hashed at issue time," not "the official proof for S05/S08/…".

## Verdict

Round-6 one-hash exploits are closed. False-green remains: **one authentic irrelevant file per surface** still launders launch-ready.

FULLY-GREEN: no
