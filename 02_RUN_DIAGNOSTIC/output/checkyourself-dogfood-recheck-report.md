# CheckYourself Dogfood Recheck Report

Generated: 2026-05-28 23:24 PDT

## Score change

Before: 84 / 100
After local remediation: 88 / 100

The score remains below 90 because the public GitHub remote and remote Actions
run have not been created or verified yet.

## Status by severity

| Severity | Before | After |
|---|---:|---:|
| P0 | 0 | 0 |
| P1 | 0 | 0 |
| P2 | 4 open | 3 fixed, 1 pending external launch |
| P3 | 6 open | 6 fixed |

## Fixed locally

- Generated scanner output is ignored.
- Dashboard manifest metadata now points to one HTML/CSS dashboard and one inline Markdown fallback.
- GitHub Actions has a broader local quality gate.
- Duplicate token-efficiency docs are removed.
- Private v1.3 release note is marked historical.
- Scanner generated header no longer references the old path.
- Dogfood/eval fixture exists.
- Dashboard smoke-check guidance exists.
- Manifest modes are less noisy.

## Remaining external gate

Create the public GitHub repository, push `main`, and verify Actions.
