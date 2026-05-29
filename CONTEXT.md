# CheckYourself Context Router

This file is the ICM-style entrypoint for agents using CheckYourself.

CheckYourself is a public, folder-based diagnostic system. It uses staged
Markdown context instead of a runtime framework. Load only the stage needed for
the user's current task, then write outputs to that stage's `output/` folder
when the user asks for files or when a handoff artifact is useful.

## Canonical Rules

1. Start read-only for diagnostics.
2. Infer the user's project stack from evidence.
3. Sweep the full coverage matrix before ranking findings.
4. Ask for approval before code, config, production, or destructive changes.
5. Keep the Markdown report as the source of truth.
6. Generate the dashboard only when the user explicitly asks for it.
7. Keep the Creator Kit and local agent state out of public releases.

## Stage Router

| User intent | Load first | Then load | Primary output |
|---|---|---|---|
| "How do I use this?" | `00_START_HERE/CONTEXT.md` | `README.md`, `START_HERE.md` | User chooses a path |
| "Map my app first" | `01_PROJECT_CONTEXT/CONTEXT.md` | `01_PROJECT_CONTEXT/README.md` | App profile or unknowns list |
| "Run a diagnostic" | `02_RUN_DIAGNOSTIC/CONTEXT.md` | `rules.md`, coverage and scoring files | Production Reality Report |
| "Fix approved issues" | `03_GUIDED_FIX_MODE/CONTEXT.md` | Diagnostic report, fix template | Approval-gated fixes |
| "Create a learning plan" | `04_LEARNING_PLAN/CONTEXT.md` | Diagnostic/remediation history | Bespoke Learning Plan |
| "Make a dashboard" | `10_DASHBOARD/CONTEXT.md` | Existing report only | Optional HTML dashboard |
| "Use advanced guidance" | `90_ADVANCED/CONTEXT.md` | Relevant capability only | Specialist checklist or plan |

## Output Handoffs

Use these folders for durable handoffs when file output is requested:

- `01_PROJECT_CONTEXT/output/`
- `02_RUN_DIAGNOSTIC/output/`
- `03_GUIDED_FIX_MODE/output/`
- `04_LEARNING_PLAN/output/`
- `10_DASHBOARD/output/`

Do not write generated outputs into source templates unless the user explicitly
asks to update the templates.

## Public Release Boundary

The public repository should include the CheckYourself product files and should
exclude:

- `checkyourself-creator-launch-kit copy/`
- `.omx/`
- `.DS_Store`
- local generated report/dashboard files unless intentionally committed
