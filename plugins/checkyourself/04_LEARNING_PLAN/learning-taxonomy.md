# Learning Taxonomy

Use this to map findings to learning topics.

| Finding type | Learning topic | Beginner version | Advanced version |
|---|---|---|---|
| Missing server-side auth check | Authorization | The server must check who can access each thing. | Object-level authorization, policy enforcement, confused deputy risks. |
| Secrets in code or unclear env handling | Secrets management | Keep keys out of code and put them in the host's secret manager. | Secret rotation, scoped credentials, CI secret exposure, repo history scanning. |
| No tests around critical behavior | Testing | Tests prove important behavior keeps working. | Contract tests, negative tests, mutation testing, CI gates. |
| No rollback path | Release safety | You need an undo button for production. | Blue/green, canary, feature flags, DB migration rollback strategies. |
| No useful logs/errors | Observability | You need clues when the app breaks. | Structured logs, traces, metrics, SLOs, alert fatigue, cardinality. |
| Cross-user data risk | Data isolation | Users should only see their own data. | RLS, tenant-scoped caches, search index isolation, differential tests. |
| AI gives unsupported answers | AI/RAG trust | Show sources and refuse when unsure. | Evaluation sets, citation grounding, prompt injection, retrieval quality, tool boundaries. |
