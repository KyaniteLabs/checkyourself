# Start Here

You are about to use CheckYourself to diagnose an app before shipping it.

The goal is not to shame the project. The goal is to make the invisible parts visible, then fix them safely with your approval.

## Choose your path

### Path 1 — Easiest

Use this when you are new, in a hurry, or working in ChatGPT/Claude/Gemini without a coding agent.

1. Open [`PASTE_THIS_INTO_YOUR_AI.md`](PASTE_THIS_INTO_YOUR_AI.md).
2. Copy the prompt.
3. Give it to your AI with your app files, repo, screenshots, exported code, or a written description.
4. Ask for the diagnostic first.

### Path 2 — Best for coding tools

Use this in Cursor, Windsurf, Claude Code, Codex, Replit, or any assistant that can read files.

1. Put this folder inside or next to your project.
2. Tell the AI: “Use the checkyourself folder as context. Start with `CONTEXT.md`.”
3. Ask it to run the diagnostic.
4. Approve fixes one at a time or in safe batches.
5. Recheck until every finding is resolved, deferred, accepted, blocked, or proven not applicable.

### Path 3 — Lowest token path

Use the beginner prompt first, then ask the AI to load deeper files only when needed.

Suggested instruction:

```text
Use only the minimum CheckYourself context needed for the current step. Load advanced references only when a specific finding requires them.
```

## Optional visual dashboard

The default report is Markdown to save tokens.

After the report exists, say:

```text
dashboard yes
```

The AI should create a self-contained HTML/CSS dashboard from the existing report. This is optional because some users prefer to save tokens.

If you want the lowest-token version, say:

```text
dashboard inline
```

The AI should return a compact Markdown dashboard instead of an HTML file.

## What you should get back

A useful diagnostic includes:

- a project map;
- an inferred stack;
- unknowns and assumptions;
- a Production Reality Score;
- a coverage sweep across all production surfaces;
- P0/P1/P2/P3 risks;
- a complete ranked findings register;
- a complete remediation backlog;
- the safest first approval batch;
- a path for continuing until every issue is resolved;
- a learning plan based on the findings and remediations.

## The most important rule

Start read-only.

The AI should inspect, explain, and recommend before it changes anything.
