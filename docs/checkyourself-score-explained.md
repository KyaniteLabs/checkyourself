# CheckYourself Score Explained

A score is useful because people need a simple signal.

A score is dangerous because people may treat it as permission to ship.

So CheckYourself uses the score as a conversation starter, not as a guarantee.

## What the score means

The score estimates production-readiness confidence based on available evidence.

## What the score does not mean

It does not mean:

- the app is secure;
- the app is compliant;
- the app has been penetration tested;
- a human expert reviewed it;
- production launch is risk-free.

## Why caps matter

If there is a P0, the score must stay low even if the rest of the project is polished.

A beautiful app that leaks user data is not production-ready.

## How to raise the score honestly

- Fix P0/P1 issues.
- Add tests for risky paths.
- Document deployment and rollback.
- Prove secrets are not hardcoded.
- Add observability.
- Verify auth and data boundaries.
- Re-run the diagnostic.
