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
