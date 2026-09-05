# CheckYourself Score Explained

A score is useful because people need a simple signal.

A score is dangerous because people may treat it as permission to ship.

So CheckYourself uses the score as a conversation starter, not as a guarantee.

## What the score means

The score estimates production-readiness confidence based on available evidence.

It is deliberately hard to game. Absence of findings is treated as absence of
evidence, not proof of safety: if the scanner finds no secrets, the secrets
surface is `Unknown`, not `Pass`. A coverage surface marked `Pass` without
reviewer assertions and verifier-captured, non-empty, hash-matched receipts, or
`NotApplicable` without a delegated-responsibility receipt, is downgraded to
`Unknown`. Required surfaces omitted from the coverage artifact also count as
`Unknown`. So omitting or hand-waving a surface never scores better than
honestly reporting it.

## Score modes and confidence

- **Coverage-backed** — you supplied a filled coverage artifact. Only this mode
  can reach `high` confidence, and only when all 20 surfaces are present with
  real evidence.
- **Scan-derived estimate** — derived from a scan with no coverage. Confidence
  stays `low`.
- **Finding-only estimate** — derived from a bare findings list. Confidence
  stays `low`.

The evidence caps below apply in **every** mode, so an estimate can never report
a launch-ready number.

## What the score does not mean

It does not mean:

- the app is secure;
- the app is compliant;
- the app has been penetration tested;
- a human expert reviewed it;
- production launch is risk-free.

## Why caps matter

Caps stop polish from hiding risk. They apply in order, and the lowest one wins:

- an unresolved **P0** caps the score at **49**;
- an unresolved **P1** caps the score at **74**;
- **missing evidence in a critical category** (data, auth, secrets) caps at **84**;
- **missing key launch-gate evidence** (tests, secrets, deploy/rollback,
  observability, auth, data boundaries) caps at **90**.

A beautiful app that leaks user data is not production-ready, so a single P0
keeps the score at 49 no matter how polished everything else looks.

Workflow dispositions do not erase residual risk: `accepted-risk`, `deferred`,
and `suppressed` findings retain their penalties and caps until the underlying
exposure is fixed or proven not applicable. The optional `--claim` input records
what completion means and marks evidence as explicitly bound or unbound; it is
not an independent challenge runner.

## How to raise the score honestly

- Fix P0/P1 issues.
- Add tests for risky paths.
- Document deployment and rollback.
- Prove secrets are not hardcoded.
- Add observability.
- Verify auth and data boundaries.
- Fill the coverage matrix with real evidence so the score is coverage-backed.
- Re-run the diagnostic, and use `diff` to confirm you fixed risk without adding new.
