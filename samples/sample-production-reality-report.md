# Sample Production Reality Report

This sample is intentionally generic. It shows the shape of a useful CheckYourself output.

## 1. Executive Summary

This app appears to be a client portal where users can log in and view account-specific records.

The UI appears functional, but the production-readiness risk is high because the diagnostic found evidence of protected frontend routes without enough evidence of server-side ownership checks. That means the app may hide records in the browser while still allowing direct API access if a user changes an ID.

## 2. Detected stack

| Area | Detected technology | Evidence | Confidence |
|---|---|---|---|
| Frontend | React/Next-style app | `package.json`, route files | Medium |
| Backend | API routes | `/api` path hints | Medium |
| Database | Unknown SQL/ORM | query helper names | Low |
| Auth | Session/JWT-style | middleware and auth filenames | Low |
| Hosting | Unknown | no deployment config found | Low |
| Testing | Not proven | no tests detected | Medium |

## 3. Production Reality Score

**Score:** 42 / 100
**Confidence:** Medium

The unresolved P0 (unverified server-side ownership checks) caps the ceiling at 49. Per-category penalties for the missing ownership check, absent tests, no rollback plan, and no error monitoring brought the score down to 42.

## 4. P0 findings

| ID | Finding | Plain-English risk | Evidence | Recommended first fix |
|---|---|---|---|---|
| P0-001 | Missing proof of object-level authorization | A logged-in user might access another user’s record by changing an ID. | Protected UI route, API path accepting IDs, no negative test found. | Add server-side user/tenant ownership check and a negative test. |

## 5. P1 findings

| ID | Finding | Plain-English risk | Evidence | Recommended first fix |
|---|---|---|---|---|
| P1-001 | No rollback plan found | If a deploy breaks, there is no documented undo path. | No release or rollback docs found. | Add a rollback checklist for deploys and migrations. |
| P1-002 | No error monitoring found | You may not know when users are hitting crashes. | No monitoring SDK/config detected. | Add basic error tracking or structured error logs. |

## 6. Complete ranked remediation backlog

| Order | Finding | Status |
|---:|---|---|
| 1 | Fix server-side ownership checks for record APIs. | Still open |
| 2 | Add negative authorization tests. | Still open |
| 3 | Write a deployment and rollback checklist. | Still open |
| 4 | Add basic error monitoring or structured error logs. | Still open |

## 7. Safest first approval batch

Start with the server-side ownership check and negative test because they address the highest-risk data exposure path. The rollback checklist and monitoring work remain in the backlog; they are not ignored.

## 8. Learning-plan seeds

| Finding | Concept to learn | Why it matters now |
|---|---|---|
| P0-001 | Server-side authorization | UI protection does not secure an API. |
| P0-001 | Negative tests | You need tests that prove bad access fails. |
| P1-001 | Rollback planning | Production needs an undo path. |
