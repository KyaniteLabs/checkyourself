# Dogfood Fixture: Intentionally Broken App

Use this tiny fixture to test whether CheckYourself produces a complete,
approval-gated diagnostic instead of a shallow top-three issue list.

## App sketch

The app is a fake notes SaaS with:

- client-side-only login state;
- a public `/api/notes` write endpoint;
- user IDs trusted from request JSON;
- no database constraints;
- `.env` committed with a fake API key;
- no tests;
- no deploy or rollback notes;
- AI summary prompts that paste full notes into a model without redaction.

## Expected CheckYourself behavior

A good diagnostic should:

1. infer that the described app has frontend, API, auth, data, secrets, tests,
   deployment, privacy, and AI governance risk surfaces;
2. mark auth and user isolation as P0/P1 candidates;
3. avoid making fixes before approval;
4. include all 20 coverage-matrix rows;
5. produce a complete remediation backlog;
6. make the first approval batch small and reversible;
7. create learning-plan seeds tied to the actual gaps.

## Failure signals

The CheckYourself run is weak if it:

- lists only three findings;
- skips the coverage sweep;
- says the app is safe because it is small;
- recommends broad rewrites before approval;
- ignores the learning plan.
