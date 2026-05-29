# CheckYourself Dogfood Learning Plan

Generated from the CheckYourself self-audit and remediation pass.

## Inferred current level

Advanced enough to build a useful diagnostic system and validation layer; next
growth area is turning local launch confidence into repeatable public proof.

## Top concepts to learn next

| Concept | Why it matters | Practice inside this repo |
|---|---|---|
| Generated artifact boundaries | Helpers should not create accidental public files. | Run every Creator Kit script and confirm `git status --short` stays clean or ignored. |
| Metadata as agent control plane | Agents use manifests and context files as instructions. | Compare README, `CONTEXT.md`, and `checkyourself.manifest.json` for routing conflicts. |
| CI parity | CI should match the checks used to call the repo ready. | Keep adding manual dogfood checks to `.github/workflows/validate.yml` or `tools/validate_public.py`. |
| Public launch proof | A local green repo is not the same as a public green repo. | After push, verify GitHub Actions, README rendering, image rendering, and release settings. |
| Agent eval fixtures | Prompt systems need sample failures to prevent shallow reports. | Run CheckYourself against `samples/dogfood-fixture-broken-app.md` and compare output quality. |

## Seven-day plan

1. Run the dogfood fixture through one AI tool and score whether all required report sections appear.
2. Push the repo to GitHub and capture the first Actions result.
3. Add any GitHub-only failure back into the local validator.
4. Open the generated dashboard and compare counts against the Markdown report.
5. Ask a weaker model to use `BEGINNER_PROMPT_ONLY.md`; record what it misses.
6. Tighten prompts or context files around any missed section.
7. Re-run the self-audit and update the remediation log.

## What to ignore for now

- Full enterprise compliance workflows.
- Multi-page dashboard systems.
- Heavy automated browser regression unless the dashboard becomes a primary product surface.
