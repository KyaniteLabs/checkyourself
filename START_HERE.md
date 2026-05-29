# Start Here

You are about to use CheckYourself to reality-check an app before shipping it.

The goal is not to shame the project. The goal is to make the invisible parts visible, then fix them safely with your approval. Expect useful side-eye, not cruelty.

## Choose Your Path

### Path 1 - Coding tools that read files

Use this in Cursor, Windsurf, Claude Code, Codex, Replit, or any assistant that can read files.

1. Put this folder inside or next to your project.
2. Tell the AI: “Use the checkyourself folder as your operating context. Start with `CONTEXT.md`.”
3. Ask it to run the read-only diagnostic.
4. Approve fixes one at a time or in safe batches.
5. Recheck until every finding is resolved, deferred, accepted, blocked, or proven not applicable.

### Path 2 - Chat-only tools

Use this when your assistant cannot read a project folder.

1. Open [`PASTE_THIS_INTO_YOUR_AI.md`](PASTE_THIS_INTO_YOUR_AI.md) — the CheckYourself bootstrap.
2. Give those operating instructions to your AI along with your app files, repo, screenshots, exported code, or a written description.
3. Ask for the diagnostic first.

### Path 3 - Optional local scan

Run the bundled scanner to detect your stack and obvious issues, then hand the generated context to your AI:

```text
python3 tools/checkyourself.py /path/to/your/project
```

It writes `CHECKYOURSELF_PROJECT_CONTEXT.generated.md` so your assistant spends tokens on judgment, not discovery. Use `--format json --no-write` when an agent or CI needs machine-readable output. The CLI is optional; every path above works without it.

### Keep Context Lean

Whichever path you use, tell the AI:

```text
Use only the minimum CheckYourself context needed for the current step. Load advanced references only when a specific finding requires them.
```

## Optional Dashboard

The default report is Markdown because it is cheaper, easier to diff, and easier for agents to update.

After the report exists, say:

```text
dashboard yes
```

The AI should create a self-contained HTML/CSS dashboard from the existing report. It should not re-run the audit just to make the dashboard.

If you want the lowest-token version, say:

```text
dashboard inline
```

The AI should return a compact Markdown dashboard instead of an HTML file.

## What You Should Get Back

A useful diagnostic includes:

- a project map;
- an inferred stack;
- unknowns and assumptions;
- a Production Reality Score with evidence and caps;
- a coverage sweep across all production surfaces;
- P0/P1/P2/P3 risks;
- a complete ranked findings register;
- a complete remediation backlog;
- the safest first approval batch, not the whole fix scope;
- a path for continuing until every issue is resolved;
- a learning plan based on the findings and remediations.

## The Most Important Rule

Start read-only.

The AI should inspect, explain, and recommend before it changes anything.
