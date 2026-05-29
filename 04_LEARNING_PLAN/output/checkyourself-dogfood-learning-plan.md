# CheckYourself Dogfood Learning Plan

Generated: 2026-05-29 03:04 PDT

## Inferred Current Level

Advanced. The project now has a real local CLI, schema contracts, a thin MCP
wrapper, CI, dashboard proof, and public/private release boundaries. The next
growth edge is keeping every generated output path as safe as the diagnostic
findings themselves.

## Language And Accessibility Mode

Primary output is English. Second-language output should be inferred at run time
from the user, project, region, docs, locale files, or explicit context, then
confirmed before producing bilingual learning/dashboard output.

Accessibility mode remains ADHD/autism/dyslexia-friendly: short sections,
literal headings, stable structure, high contrast, no motion-dependent meaning,
and concrete success signals.

## Top Concepts To Learn Next

### 1. Redact Generated Output, Not Just Findings

**Plain English:** A scanner can detect a secret and still leak it somewhere
else. Every generated output path needs redaction, including package scripts,
Markdown context files, JSON summaries, dashboards, and logs.

**Triggered by:** `CY-REVIEW-001`, GitHub PR review comment about package
scripts leaking credential-shaped values.

**Do this next:** When adding any new output field, ask: "Could this contain a
credential, token, private URL, or customer data?" If yes, redact before writing
and add a regression test.

**Success signal:** A fake token in `package.json` scripts does not appear in
scan JSON or generated Markdown.

**Trusted written source:** [GitHub Docs: Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

**Why this source is trusted:** GitHub owns the repository hosting surface and
maintains the official guidance for secret exposure.

**Relevant video:** [GitHub Secret Scanning](https://www.youtube.com/watch?v=l0YsEk_59fQ)

**Video trust note:** Official GitHub channel.

### 2. A 100 Score Needs Coverage Evidence

**Plain English:** A clean scan is not the same as a complete audit. The score
should reach 100 only when coverage proves every applicable production surface
or names a clear not-applicable reason.

**Triggered by:** `CY-EVIDENCE-001`, the CLI correctly capped the score when it
had findings but no coverage evidence.

**Do this next:** Pair every final score with a coverage artifact and the exact
command that reproduces the score.

**Success signal:** `coverage --check` passes, and `score --findings ... --coverage ...`
returns `100`, high confidence, and no caps.

**Trusted written source:** [CheckYourself scoring method](../../02_RUN_DIAGNOSTIC/scoring-method.md)

**Why this source is trusted:** It is the repository's canonical scoring
contract and is enforced by the CLI.

**Relevant video:** [Evals in Action: From Frontier Research to Production Applications](https://www.youtube.com/watch?v=YEaKXjHENyQ)

**Video trust note:** Official OpenAI channel; useful framing for evidence-based
AI evaluation.

### 3. Static Projects Still Need Support And Security Triage

**Plain English:** No server does not mean no incidents. Users still need a
safe path to report bugs, stale docs, accessibility issues, MCP failures, and
security concerns.

**Triggered by:** `CY-OPS-001`, maintainer triage was not documented.

**Do this next:** Keep `SUPPORT.md`, `SECURITY.md`, and the issue template in
sync with the README and GitHub About section.

**Success signal:** A user can report a redacted bug or security concern without
guessing where it belongs.

**Trusted written source:** [GitHub Docs: Configuring issue templates for your repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/configuring-issue-templates-for-your-repository)

**Why this source is trusted:** GitHub maintains the issue-template behavior
used by this repository.

**Relevant video:** [How to use GitHub Issues](https://www.youtube.com/watch?v=TJlYiMp8FuY)

**Video trust note:** Official GitHub channel.

## Seven-Day Plan

1. Add one redaction test for every new output surface.
2. Run `coverage --check` before accepting any score above 90.
3. Review `SUPPORT.md` and `SECURITY.md` after the first external issue.
4. Run the MCP smoke test in at least one real MCP client.
5. Re-run the dogfood fixture through one target agent.
6. Refresh dashboard proof after any major score or UI change.
7. Tag the first release once launch copy is final.

## What To Ignore For Now

- Hosted API work.
- Multi-user SaaS support flows.
- Enterprise compliance process.
- Full visual-regression infrastructure unless dashboards become a primary
  user-facing product surface.
