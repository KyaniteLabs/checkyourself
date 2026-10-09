# Testing & Quality Gates Reference

## Risk-based test matrix

| Risk | Test types |
|---|---|
| Pure logic | Unit, property tests |
| API contract | Contract, integration, compatibility tests |
| Database changes | Migration, rollback/roll-forward, data parity tests |
| Auth/tenant isolation | Negative authorization tests, dual-tenant fixtures |
| UI critical flow | E2E, accessibility, visual sanity where useful |
| Performance claim | Benchmark/load test with representative data |
| AI behavior | Evals, retrieval/citation checks, safety cases |

## Flake policy

A flaky test is a production signal. Quarantine only with owner, rationale, and expiration.
