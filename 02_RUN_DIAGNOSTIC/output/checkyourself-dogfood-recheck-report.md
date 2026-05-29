# CheckYourself Dogfood Recheck Report

Generated: 2026-05-29 00:49 PDT

## Score change

Before: 84 / 100
After local remediation: 88 / 100
After public GitHub proof: 92 / 100

The score is now above 90 because the public GitHub repository exists and the
remote GitHub Actions validation run passed.

## Status by severity

| Severity | Before | After |
|---|---:|---:|
| P0 | 0 | 0 |
| P1 | 0 | 0 |
| P2 | 4 open | 4 fixed |
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

## Public launch proof

- Public repo: https://github.com/KyaniteLabs/checkyourself
- Remote: `origin` -> `https://github.com/KyaniteLabs/checkyourself.git`
- GitHub Actions: `Validate CheckYourself` run `26625079272` completed with success.
