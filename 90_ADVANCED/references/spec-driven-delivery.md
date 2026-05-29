# Spec-Driven Delivery Reference

## Buildable specification outline

1. Problem and target users
2. User journeys and non-goals
3. Data model and ownership
4. API/event/file contracts
5. Permission model
6. UX states and accessibility expectations
7. Failure modes and fallback behavior
8. Observability signals
9. Acceptance criteria
10. Rollout and rollback plan

## Human checkpoints

- Priorities review: is this the right work?
- Spec review: is this the right contract and architecture?
- Intent-to-ship review: has the implementation met the spec and gates?

## Contract formats

Use OpenAPI for HTTP APIs, AsyncAPI for event-driven APIs, JSON Schema for structured inputs/outputs, SQL migrations for database change evidence, and ADRs for architectural decisions.
