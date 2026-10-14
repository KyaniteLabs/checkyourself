# Diagnostic Philosophy

The diagnostic is designed for people who may not know what they do not know.

That means the AI must not simply ask, “Do you have observability?” A beginner may not know what that means.

Instead, the AI should ask or inspect concrete evidence:

- Where do errors go when the app crashes?
- Can you tell which user triggered a failed request?
- Is there a place you would see a spike in failures?
- Do you have a rollback path if a deploy breaks?
- Can User A access User B’s data by changing an ID?

The goal is interpreted context: the AI maps visible project artifacts to invisible production risks.
