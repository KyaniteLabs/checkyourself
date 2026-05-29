# Sample Bespoke Learning Plan

## Based on

- Diagnostic score: 42/100
- Main risk pattern: app works in the UI, but server-side production controls are not proven.

## Inferred current level

**Intermediate beginner / early builder.**

Evidence: the project has a working app structure, but production concepts like authorization tests, rollback, and monitoring were missing or not documented.

## Top 5 concepts to learn next

| Priority | Concept | Triggering finding | Why it matters for this app | Level | Learn now or later |
|---:|---|---|---|---|---|
| 1 | Server-side authorization | P0-001 | Users must only access their own records even if they call the API directly. | Beginner → Intermediate | Now |
| 2 | Negative testing | P0-001 | You need tests that prove the dangerous thing does not happen. | Beginner | Now |
| 3 | Secrets management | Unknown env handling | API keys must not live in code or screenshots. | Beginner | Now |
| 4 | Rollback planning | P1-001 | You need an undo path if a deploy breaks. | Intermediate | Soon |
| 5 | Error monitoring | P1-002 | You need to know when users hit crashes. | Beginner | Soon |

## 7-day practical plan

### Day 1

Learn the difference between authentication and authorization. Find one API route that returns user-specific data.

### Day 2

Add or write down the rule for who is allowed to access that data.

### Day 3

Add a negative test: User A tries to access User B’s data and gets rejected.

### Day 4

Review environment variables. Make sure no real secret values are committed.

### Day 5

Write a rollback checklist for your deployment platform.

### Day 6

Add basic error logging or monitoring.

### Day 7

Re-run CheckYourself and compare the score.

## What to ignore for now

- Kubernetes.
- Multi-region deployment.
- Complex service mesh observability.
- Advanced chaos engineering.

Those may be useful later, but they are not the next bottleneck for this app.
