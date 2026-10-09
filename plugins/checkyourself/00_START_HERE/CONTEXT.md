# Start Stage Context

Use this stage when the user is deciding how to run CheckYourself or needs the
shortest safe entrypoint.

## Inputs

| Input | Required? | Notes |
|---|---|---|
| User skill level or comfort | No | Infer gently from what they ask. |
| Tool environment | No | Chat-only, coding agent, local repo, or unknown. |
| Project access level | No | Files, screenshots, exported code, or description. |

## Process

1. Keep the explanation short and plain.
2. Route the user to one of the paths in `START_HERE.md`.
3. If they want a diagnostic, hand off to `02_RUN_DIAGNOSTIC/CONTEXT.md`.
4. If they only have a description or screenshots, ask for the smallest useful
   context instead of requesting the whole project.

## Outputs

| Output | Where |
|---|---|
| Recommended user path | Chat response |
| Optional next prompt | Chat response |

## Do Not

- Do not run a diagnostic from this stage.
- Do not generate a dashboard.
- Do not load the advanced capability pack unless a specific risk surface
  requires it.
