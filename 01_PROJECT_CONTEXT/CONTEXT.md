# Project Context Stage

Use this stage to build the app map before scoring or fixing.

## Inputs

| Input | Required? | Notes |
|---|---|---|
| Project files or repo access | Preferred | Infer stack from files and configs. |
| App description | Preferred | Helps identify users and harm model. |
| Known deployment target | Optional | Treat as unknown unless evidenced. |
| Existing report | Optional | Use only as context, not as proof. |

## Process

1. Read `01_PROJECT_CONTEXT/README.md`.
2. Fill or mentally apply `app-profile-template.md`.
3. Track missing facts in `unknowns-and-assumptions.md`.
4. Separate evidence, inference, and unknowns.
5. Hand off to diagnostic only after the app purpose, visible stack signals, and
   major unknowns are clear enough to score honestly.

## Outputs

| Output | Where |
|---|---|
| App profile | `01_PROJECT_CONTEXT/output/app-profile.md` when file output is requested |
| Unknowns list | `01_PROJECT_CONTEXT/output/unknowns.md` when file output is requested |
| Inline summary | Chat response |

## Handoff

Pass the app profile and unknowns to `02_RUN_DIAGNOSTIC/CONTEXT.md`.

## Do Not

- Do not assume framework, database, auth, hosting, or model provider.
- Do not score the app from this stage alone.
