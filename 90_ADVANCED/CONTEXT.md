# Advanced Capability Stage Context

Use this stage only when a specific finding or user request needs deeper
production-hardening guidance.

## Inputs

| Input | Required? | Notes |
|---|---|---|
| Finding or risk surface | Yes | Pick the relevant capability, not the whole pack. |
| Project evidence | Yes | Use direct files, configs, tests, or logs. |
| Desired output | Preferred | Plan, checklist, review, template, or explanation. |

## Process

1. Read `90_ADVANCED/MANIFEST.yaml` to choose the smallest relevant capability.
2. Load only that capability's `SKILL.md` or supporting reference.
3. Keep the output tied to the current diagnostic finding.
4. Return practical gates, checks, or remediation guidance.

## Outputs

| Output | Where |
|---|---|
| Specialist checklist or plan | Chat response |
| Optional advanced artifact | Caller-selected `output/` folder |

## Do Not

- Do not load every advanced reference by default.
- Do not turn beginner diagnostics into an enterprise compliance dump.
- Do not replace the Production Reality Report as the source of truth.
