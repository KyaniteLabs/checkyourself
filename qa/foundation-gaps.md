# Foundation gaps and reconciliation

Baseline: GitHub main `7f09fd0`. This change adds the missing architecture/product
owner map, read-before-work instruction and executable inventory checks. No
runtime, credential, deployment or production settings changes are intended.
Rollback: revert this PR; no persistent service migration is involved.

## Verification baseline and remediation

- Baseline `python3 -m unittest discover -s tests`: 155 tests PASS, Python 3.12.3.
- Baseline public validator and size discipline: PASS.
- Missing architecture policy test reproduced as failing before adding the
  inventory; added `tests/test_architecture_contract.py` to the existing unittest
  discovery lane, requiring exact identity/schema, nonempty tracked matches,
  sensitive runtime/configuration/automation coverage and read-first docs.
- Existing GitHub CI exercises CLI/MCP, Ruff, public shape, size and secrets;
  Forgejo CI independently exercises CLI/MCP and unit tests. Presence is not
  execution. Hosted exact-head results must be read after publication by Security.

## Remaining gaps, accountable route

| Gap | Evidence/limit | Accountable next action |
| --- | --- | --- |
| Mirror reconciliation | Authorized mapping, visibility, default SHA, branch sync and forge-specific runs not supplied to this worker. Requested on gate t_0a3d68a5; no denied credential probing. | Platform supplies sanitized mapping and exact revision/run evidence. Security verifies reconciliation before estate adoption; do not copy public content to an unverified mirror. |
| Native plugin integration drift | Open PRs #50/#51 propose native Hermes integrations; #41 proposes Claude packaging. They are not in this baseline. | Engineering updates docs/path inventory if those proposals merge; Product must not describe them as shipped here. |
| Browser/deployment E2E | Landing/dashboard HTML and historical screenshots exist, but neither forge workflow runs browser assertions. No live hosting proof in this change. | Engineering/Design add a separately scoped reproducible browser smoke when changing UI; no web-service safety claim from CLI tests. |
| Container E2E | Dockerfile is non-root and copies engine/schema, but existing CI does not build/start it. | Engineering adds image build + stdio startup verification through authorized workflow publication. No image execution claimed here. |
| Forge lint parity remediated | Baseline Forgejo pinned Ruff 0.15.8 and omitted format/size gates. This PR aligns to GitHub's 0.16.5 and adds format/size commands. Local Ruff/check/format and size execution pass; hosted mirror execution remains unproved. | Platform/Security verify the mirrored revision and forge run; local checks are not a mirror CI receipt. |
| Challenge subprocess boundary | Challenge execution and receipt re-execution can run project argv with process privileges. A local integrity key is not independent custody. | Security reviews these existing boundaries; this documentation makes no isolation or independent-authorship claim. |

No repository exclusion or partial-estate adoption is authorized. Product reviews
PRODUCT.md and user-facing architecture descriptions first, then routes to
Security for exact-head CI, exposure, secrets, blast radius, rollback and merge.
The builder must not merge. Root t_2210091a remains responsible for full-estate
reconciliation and any separately routed foundation work.
