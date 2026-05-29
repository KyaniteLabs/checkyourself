# Examples

## Example diagnostic language

Instead of:

> Your auth implementation is insufficient.

Say:

> Your app appears to know whether a user is logged in, but I do not see proof that it checks whether the user is allowed to access each specific record. That matters because a logged-in user might still be able to view another user’s data if an API route forgets to filter by user or tenant.

## Example approval prompt

> I recommend fixing the missing server-side ownership check on `GET /api/invoices/:id` first. This is a P0 because it could expose another user’s invoice. The smallest fix is to add a user/tenant ownership condition to the database query and add a negative test. I expect to touch `api/invoices/[id]`, the invoice query helper, and one test file. May I make this fix?

## Example learning-plan item

> Learn: server-side authorization checks.
>
> Triggered by: the diagnostic found protected routes in the frontend but no matching ownership check in the API.
>
> Why it matters: hiding a button in the UI does not stop someone from calling the API directly.
>
> Tiny exercise: write one test where User A tries to access User B’s record and the server rejects it.
