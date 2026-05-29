# Token Efficiency

Canonical guidance lives in [`token-efficiency-and-context-control.md`](token-efficiency-and-context-control.md).

Short version:

1. Load only the context needed for the current stage.
2. Keep the findings register complete but compact.
3. Expand details for P0/P1 findings and the next approval batch.
4. Do not generate dashboard HTML unless the user asks for it.
5. Use `dashboard inline` for the compact Markdown dashboard fallback.
6. Never hide findings to save tokens.
