# Sample Production Reality Report

This sample is intentionally generic. It shows the shape of a useful CheckYourself output.

## 1. Executive Summary

**Observed:** The repository contains client-portal routes and account-record UI language.

**Inferred:** The app is intended to let authenticated users view account-specific records.

**Untested:** The available sample evidence does not establish which server, database, or deployment currently enforces ownership.

The UI appears functional, but the production risk is high because the diagnostic found protected frontend routes without a verifier-captured receipt for server-side ownership checks. That means the app may hide records in the browser while still allowing direct API access if a user changes an ID.

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
**Confidence:** Low

The unresolved P0 (unverified server-side ownership checks) caps the ceiling at 49. The score is a bounded estimate because the sample has not established the deployment target or captured verifier-owned receipts.

## 4. P0 findings

| ID | Finding | Plain-English risk | Evidence | Recommended first fix |
|---|---|---|---|---|
| P0-001 | Missing proof of object-level authorization | A logged-in user might access another user’s record by changing an ID. | **Observed:** protected UI route and API path accepting IDs. **Untested:** no negative authorization receipt. | First run a tenant-A-to-tenant-B access challenge against the captured revision; change code only if it fails. |

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

Start with a decisive check: run a tenant-A-to-tenant-B access attempt against the captured revision and record the result. If it fails, add the smallest server-side ownership fix and negative test; if it passes, update the finding with the receipt instead. The rollback checklist and monitoring work remain in the backlog; they are not ignored.

## 8. Learning-plan seeds

| Finding | Concept to learn | Why it matters now |
|---|---|---|
| P0-001 | Server-side authorization | UI protection does not secure an API. |
| P0-001 | Negative tests | You need tests that prove bad access fails. |
| P1-001 | Rollback planning | Production needs an undo path. |
