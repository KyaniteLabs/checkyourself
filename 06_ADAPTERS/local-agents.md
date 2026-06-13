# Local Agents

Use CheckYourself with any local or repo-aware AI assistant that can read files.

Recommended flow:

1. Put this folder beside or inside the repo.
2. Point the file-aware tool at `CONTEXT.md` first — this is the canonical router that loads the right stage context.
3. Ask the assistant to read `START_HERE.md`, `AGENTS.md`, and `02_RUN_DIAGNOSTIC/coverage-matrix.md`.
4. Ask for a read-only diagnostic.
5. Approve fixes one at a time or in safe batches.
6. Re-run the diagnostic after each batch.

Keep the advanced folder unloaded until the assistant needs a specific domain.
