---
name: checkyourself
description: >-
  Use when finished work claims to be done, tested, working or ready to ship.
  Re-derive each claim from the work and label it CONFIRMED, REFUTED or
  UNVERIFIABLE with evidence, using the checkyourself_scan and checkyourself_next
  tools for the launch-risk sweep.
---

# CheckYourself

"Done" should mean proven, not said. This skill checks the claims finished work makes about itself before anyone believes them. The work's own summary is a claim to check, never evidence for itself. If you did the work, say that you are checking your own work, and treat a launch-critical claim with extra suspicion.

## Steps

1. **List the claims.** Take them from the completion report, the commit message, the diff, the README or the request. Spell out what is implied: "done" implies "it runs", "shipped" implies "reachable where it was sent", and "all links live" implies that each link resolves.
2. **Re-derive each claim from the work, the way its user would meet it.** Run the command, open the page, or read the file as it was shipped. Prefer the path a user takes over the path the author shows you.
3. **Run the scan.** Call `checkyourself_scan` on the project folder; pass `deep: true` before a launch. It reads files only and never runs project code. Then call `checkyourself_next` for what to fix first.
4. **Label every claim with its evidence.**
   - **CONFIRMED**: what you ran and what you saw, such as a command and its output line, or a file and line quoted.
   - **REFUTED**: the evidence, and what is true instead.
   - **UNVERIFIABLE**: what is missing to check it, such as access, a tool, time or credentials. Never drop it and never guess.
   - `n/a` only when the subject does not exist in this work, with the reason. "Not tested" is not a label.
5. **Lead with the verdict.** Start with one line that says whether the claim of completion is true. Then give the counts (confirmed, refuted, unverifiable) and the evidence for each claim. If a launch-critical claim is REFUTED, say in those words that the work is not done.

## How to read the scan

- **No findings means Unknown, not a pass.** The scan sees only what files show.
- **The score is the CLI's, never yours.** Without coverage evidence it is a low-confidence estimate, so say so. Never invent or round a number.
- **Findings are evidence to re-check, not a verdict.** A finding can be stale or a false positive; confirm it in the file before you report it.
- **`checkyourself_next` orders work; it is not a safety review.** Check dependencies and blast radius first.

## Boundaries

- Stay read-only. Don't edit code, install dependencies, rotate secrets or touch production without the user's yes to a named fix. After an approved fix, re-derive the claims it touched.
- Never put secrets, customer data or `.env` values in your reply.
- How a page looks and its accessibility belong to TasteCheck. Hand rendered UI to a TasteCheck audit instead of judging it here.
- For regulated, financial, health, legal, safety-critical or security-critical systems, recommend review by a qualified expert.
