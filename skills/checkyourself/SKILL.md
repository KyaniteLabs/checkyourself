---
name: checkyourself
description: >-
  Use when completed work makes claims — "done", "tests pass", "it works", "ready
  to launch" — that must be verified before they are believed. Re-derive each claim
  from the work itself and report CONFIRMED / REFUTED / UNVERIFIABLE with evidence.
  Fast claim-verification by default; the deterministic production-readiness CLI
  when launch stakes justify it.
---

# CheckYourself

The job: independently re-derive the claims completed work makes about itself and
report each as CONFIRMED, REFUTED, or UNVERIFIABLE with evidence — so "done" means
proven, not asserted. Never grade your own homework from memory: the author's
summary is a claim to check, never evidence for itself. When the verifier is the
same agent that did the work, say so and discount accordingly — use a fresh context
or a second agent for launch-critical claims.

## Protocol (both lanes)

1. **Extract the claims.** From the completion report, commit message, diff, README,
   doc, or the request. Make implicit claims explicit — "done" implies "it runs";
   "shipped" implies "reachable at its destination"; "13 works, every one live"
   implies each URL resolves.
2. **Re-derive each claim from the work, in the consumer's frame.** Run the command,
   open the page, read the file as shipped. Prefer the path a consumer would hit
   over the path the author would show you.
3. **Label with evidence:**
   - **CONFIRMED** — what you ran and saw: command + output line, URL + selector +
     observation, file:line quote.
   - **REFUTED** — the evidence plus what is actually true.
   - **UNVERIFIABLE** — what is missing to check it (access, tool, time,
     credentials). Never silently dropped, never guessed.
   - `n/a` only when the claim's subject genuinely does not exist in this work,
     with the reason. "Not tested" is not a label.
4. **Report verdict-first.** One line answering "is the claim of completion true?",
   then X confirmed / Y refuted / Z unverifiable, then the per-claim evidence list.
   Plain-English risk before technical detail. If a launch-critical claim is
   REFUTED, say the work is not done in those words.
5. **Stay read-only.** No edits, dependency installs, secret rotation, or
   production changes without an explicitly approved named fix. After an approved
   fix: smallest reversible change, re-derive the affected claims, update status,
   rescore if evidence changed. Accepted or deferred findings stay visible as
   residual risk with owner and trigger.
6. **Safety.** No secrets, customer data, or unredacted `.env` values in output.
   For regulated, financial, health, legal, life-safety, security-critical, or
   high-volume systems, recommend qualified expert review.

## Fast lane (minutes)

Claims → re-derive → verdict list. Examples: "tests pass" (run the suite; quote the
summary line), "all links live" (fetch each; list statuses), "this doc matches the
repo" (read the file as shipped at this revision), "the page says N items" (count
them in the rendered DOM, not the source string). Label what cannot be checked in
this harness UNVERIFIABLE with the reason — a scoped honest verdict beats a fake
complete one.

## Deep lane (launch / production readiness)

When the question is "may this go to production", coverage must be swept, not
sampled. Use the CheckYourself CLI (stdlib-only, read-only, no network, no
telemetry):

```
CY=~/workspaces/checkyourself/tools/checkyourself.py
python3 $CY describe --format json
python3 $CY scan <path> --deep --format json --no-write
python3 $CY coverage --emit            # fill with evidence, then:
python3 $CY score --findings scan.json --coverage coverage.json --format json
python3 $CY backlog --findings scan.json --format json
python3 $CY next    --findings scan.json --format json
python3 $CY diff --old baseline.json --new current.json --ci   # regression gate
```

If the CLI is missing (repo moved), sweep manually, reuse the registry IDs below,
and label every score hand-computed. The score is always the CLI's — never invent
or hand-wave a number: `min(base, cap)` with caps 49 (unresolved P0), 74 (unresolved
P1), 84 (missing critical evidence), 90 (missing launch-gate evidence). **No
findings is Unknown, never automatic Pass.**

Sweep the surfaces that matter to this artifact: purpose, frontend UX/accessibility,
backend/API, auth, data/migrations, secrets/config, tests, CI/CD, dependencies,
deploy/rollback, observability, performance, privacy, compliance, and AI/RAG/agent
governance when relevant. Every claim needs Pass-with-evidence / Finding /
Unknown / Not-applicable-with-reason.

Manual fallback registry — stable IDs for citation, suppression, and diff; never
invent or renumber:

| Rule ID | Condition (canonical) |
|---|---|
| `CY-MANUAL-AUTH-001` | Auth, permission, session, or admin behavior lacks verified server-side evidence. |
| `CY-MANUAL-DATA-001` | Data storage, recovery, retention, or tenant isolation lacks verified evidence. |
| `CY-MANUAL-PRIVACY-001` | Privacy, consent, deletion, or third-party data handling lacks verified evidence. |
| `CY-MANUAL-TEST-001` | A dangerous or launch-critical path lacks a focused test receipt. |
| `CY-MANUAL-RELEASE-001` | Deployment, rollback, CI/CD, or supply-chain behavior lacks a verified receipt. |
| `CY-MANUAL-OBS-001` | Observability, alerting, or incident response lacks a verified receipt. |
| `CY-MANUAL-AI-001` | AI/RAG/agent permissions, evaluation, or refusal behavior lacks verified evidence. |
| `CY-MANUAL-OTHER-001` | A material gap matching no other registered condition. |

Every finding carries: rule/detector ID, severity, exact dated evidence,
plain-English risk, and status. When a shipped detector matches, reuse its detector
ID from the project's canonical registry instead of a manual one.

## Example prompts

```text
Use $checkyourself to verify the claims in this completion report. Read-only;
label each CONFIRMED / REFUTED / UNVERIFIABLE with evidence.
```

```text
Use $checkyourself to run the production-readiness scan and score on this app
before launch, list every blocking unknown, and propose the safest first fix
batch. Do not change code.
```

`dashboard inline` after a report adds a compact Markdown dashboard; there is no
dashboard by default.
