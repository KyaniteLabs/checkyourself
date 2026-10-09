# Evaluation Prompts

Use these prompts to test routing and output quality.

## Orchestrator

> Here is my app architecture. Make it production ready and tell me what is missing.

Expected: routing plan, risk register, readiness gates, staged implementation.

## Multi-tenancy

> We are adding organizations/workspaces to a shared Postgres database. Review the isolation design.

Expected: RLS policy, tenant context, cache scope, bypass matrix, dual-tenant negative tests.

## AI/RAG

> We are launching a RAG support chatbot for customers. Harden it for production.

Expected: access-controlled retrieval, citations, evals, prompt injection controls, telemetry, human escalation.

## Deployment

> This migration and API change need to ship with zero downtime. What is the release plan?

Expected: expand/backfill/contract sequence, canary/rollback, smoke tests, telemetry.

## Incident

> Latency spiked after the last deploy. Analyze the likely root cause from these logs and metrics.

Expected: timeline, facts/hypotheses/actions, telemetry gaps, rollback or mitigation options.
