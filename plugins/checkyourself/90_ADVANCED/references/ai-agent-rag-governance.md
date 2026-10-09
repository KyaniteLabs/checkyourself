# AI/RAG & Agent Governance Reference

## RAG hardening checklist

- Corpus inventory and ownership
- Access control before retrieval
- Chunking strategy and source metadata
- Citation granularity
- Freshness/staleness handling
- Retrieval evals
- Answer faithfulness evals
- Safety refusal cases
- User feedback collection
- Monitoring and drift review

## Prompt-injection defenses

The core sink is **untrusted text concatenated into a prompt or tool call**. Any string built with user input, retrieved documents, web-fetched pages, tool outputs, email/chat bodies, or file contents is attacker-controlled. Treat all of it as data, never as instructions.

What an auditor looks for in code:

- **String concatenation of user/retrieved content into the prompt** — e.g. `` prompt = f"System rules...\n{user_input}" `` or appending RAG chunks directly into the system message. This is the primary injection vector. Untrusted content must go in a clearly delimited user-role message, never the system prompt.
- **No input/output trust boundary.** Untrusted text should be wrapped (delimiters, XML-like tags, or a separate message role) and the model instructed to treat it as data. Retrieved documents in RAG are untrusted by default — a poisoned document can carry "ignore previous instructions" payloads.
- **Tool access is not allow-listed.** Agents should expose a fixed, enumerated tool set per task. Look for dynamic tool registration from model output, `eval`-style tool dispatch, or a single "run shell" / "run code" tool with no command allow-list.
- **No human-in-the-loop on high-impact tools.** Sending email, moving money, deleting data, or writing to prod must require approval (see autonomy levels below), not fire on raw model output.
- **Output used to drive privileged actions without a confirmation step** (the "confused deputy" pattern): model reads an attacker's document, the document says "email the user's data to X", and the agent's email tool obeys.

Detectable red flags: f-strings/`+`/`.format()`/template literals assembling prompts from request bodies or retrieved text; tool routers that `getattr`/`eval`/`exec` on a model-chosen name; no separation between system instructions and user data; web/file fetch results piped straight into the next prompt with no sanitization.

## PII and secrets in prompts, traces, and logs

Full-context logging is a leak. LLM apps commonly log the entire prompt, the full retrieved context, and the raw completion to a tracing backend (LangSmith, Langfuse, Helicone, Phoenix, OpenTelemetry, or `console.log`). That captures everything the user pasted plus everything retrieval pulled — PII, auth tokens, internal docs — and ships it to a third party.

Redact **before** the log/trace call, not after:

- API keys, bearer tokens, session cookies, `Authorization` headers
- Emails, phone numbers, full names, addresses, government IDs (SSN/passport)
- Payment data (PAN/card numbers, CVV), bank/account numbers
- Internal hostnames, connection strings, secrets surfaced via tool output

What an auditor looks for:

- Trace/log calls that pass the **raw** prompt, context, or messages array with no redaction pass.
- Provider keys printed in logs or echoed in error messages.
- Retrieval results logged verbatim (the retrieved corpus may contain other tenants' data).
- Prompts/completions persisted to an analytics store or vendor with no DPA, retention limit, or PII scrubbing.
- LLM provider data-retention/training settings left at defaults (confirm zero-retention / no-training where required by contract).

Remediation: a redaction middleware on the logging path, allow-list of fields safe to log, hashing or truncating user content, and a retention TTL on trace storage.

## Runaway cost and infinite-loop controls

Autonomous agents loop: think → call tool → observe → think. Without caps, a stuck agent (or an injected "keep trying forever" instruction) burns tokens and money indefinitely.

Required controls, each independently checkable:

- **Max-iteration cap** on the agent loop (e.g. `maxSteps` / `max_iterations`, hard `while step < N`). A loop with no step ceiling is a defect.
- **Per-request token budget** — cap input+output tokens per call and total tokens per task; abort when exceeded.
- **Wall-clock timeout** on the whole agent run and on each tool/model call (`AbortController`/`signal`, request timeout). Edge/serverless functions also have their own timeout — the loop must finish inside it.
- **Loop/repeat detection** — break if the agent repeats the same tool call with the same args, or makes no progress for K steps.
- **Concurrency and rate limits** per user/tenant so one session can't fan out unbounded sub-agents or tool calls.
- **Spend alerting / hard budget** at the provider (e.g. usage limits) plus per-user quotas in the app.

What an auditor looks for: an agent loop with no iteration ceiling, no timeout on model/tool calls, no token accounting, recursive sub-agent spawning with no depth limit, and no per-user/tenant rate limit on expensive endpoints.

## Output validation — never act on raw model output

Model output is untrusted. Validate structure and bounds before any code consumes it, and **never `eval`/`exec`/`new Function` model output** or pass it unescaped into a shell, SQL query, file path, or URL.

- **Schema-validate** structured output (Zod, Pydantic, JSON Schema, tool-call argument validation) before acting. Reject and re-ask on failure; do not "best-effort parse".
- **Parameterize** anything derived from model output: SQL via bound parameters (never string-built queries), shell via arg arrays (never `shell: true` with model text), file paths checked against a base dir (no traversal), URLs against an allow-list (no SSRF).
- **Bound and authorize tool arguments** — clamp amounts, IDs, ranges; re-check that the *user* (not just the model) is authorized for the resource the model named.
- **Validate citations** in RAG: the cited source must actually contain the claim; reject fabricated/unsupported citations.

Detectable red flags: `eval`/`exec`/`new Function`/`child_process` on model text; SQL built by interpolating model output; tool functions that trust `args` without validation; JSON parsed from the model with no schema check and no error path.

## Context-window cost controls

- Cap retrieved chunks (top-k) and total context tokens; don't stuff the whole corpus.
- Summarize/compact long histories instead of resending full transcripts each turn.
- Use the cheapest model that meets quality (route by task); reserve large-context calls for cases that need them.
- Cache retrieval results and reuse stable system prompts (prompt/context caching) to cut repeat input cost.
- Truncate or window tool outputs before feeding them back into the model.

## Eval and regression harness for prompts

Prompts and chains are code; changing a prompt, model version, or retrieval setting can silently regress. Require a versioned eval suite, not vibes.

- A fixed **golden set** of inputs with expected behavior, run in CI on any prompt/model/chain change.
- Metrics: retrieval quality (recall/precision on known-relevant docs), answer faithfulness/groundedness (claims supported by context), refusal correctness on unsafe/out-of-scope inputs, and regression checks against prior outputs.
- **Injection/red-team cases** in the suite (documents and inputs that attempt instruction override, data exfiltration, tool misuse) that must fail to compromise the agent.
- Pin and record model + prompt versions per eval run so regressions are attributable.
- Block deploy on eval-score drop below threshold.

What an auditor looks for: no eval harness at all, prompts edited with no test, no golden set, no injection cases, model version unpinned, and no CI gate tying prompt changes to eval results.

## Agent autonomy levels

| Level | Description | Allowed actions |
|---|---|---|
| 1 Read-only | Observe and summarize | Read docs, code, telemetry |
| 2 Advised | Recommend actions | Produce commands/patches for human review |
| 3 Approved execution | Execute after explicit approval | Bounded scripts, tests, safe deploy steps |
| 4 Bounded autonomous | Execute pre-cleared low-risk tasks | Reversible, observable, policy-approved actions only |

## Two-signal gate

Execution requires both:

- Trust signal high enough: diagnosis quality, evidence, historical success, test confidence.
- Risk signal low enough: bounded blast radius, reversibility, no sensitive data or production-impacting scope.

If either fails, escalate to a human.
