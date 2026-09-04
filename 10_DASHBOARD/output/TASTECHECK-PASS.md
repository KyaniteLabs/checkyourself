# TASTECHECK RECEIPT — CheckYourself dashboard + README — 2026-09-04

Spec (inferred system, existing artifacts): **"A calm, high-contrast dark
*instrument* — production-readiness as a readout, not a marketing page.
Kyanite signal colors (cyan/amber/magenta) on near-black panels, monospace for
data and labels, no motion, accessibility as a default."** The README landing
page inherits the same brand voice: direct, evidence-first, light side-eye at
the project state — never the person.

This receipt was refreshed against the repository state on 2026-09-04. The
existing dashboard artifact and its committed PNG were checked; W8 did not
rerender the dashboard.

## Dashboard (`checkyourself-dogfood-dashboard.html`)

| Check | Result | Notes (measured) |
|-------|--------|------------------|
| Cold load (gate-audit.js, fresh load) | ✓ | 0 fails in the existing 2026-06-12 receipt: no hidden-content, error-state, busy-state, opacity, or stuck-skeleton defects |
| Structural tells (gate-audit.js) | ✓ (1 reviewed warn) | Risk-count grid is data, not decorative social proof |
| Display face (computed) | ✓ | Existing receipt resolves to "Plus Jakarta Sans" |
| Color contrast (WCAG, measured) | ✓ | Existing receipt's measured pairs are all above 4.5:1 |
| Responsive @ 320px | ✓ | Existing receipt measured 0px horizontal overflow |
| Reduced motion | ✓ | Existing receipt found the required `prefers-reduced-motion` rule |
| Keyboard / a11y structure | ✓ | Existing receipt found skip-link, focus-visible outlines, keyboard-scrollable table regions, and score meter semantics |
| Current proof | ✓ with baseline note | Current scan: 234 files, zero open findings; current score: 100/high confidence; coverage: complete |
| Console | ✓ | Existing receipt recorded only a local `favicon.ico` 404 |

**Dashboard gate: PASS** for the existing dashboard artifact, with the
historical mechanical receipt clearly labeled above.

## README landing page (`README.md`)

| Check | Result | Notes |
|-------|--------|-------|
| License claim | ✓ | Apache License, Version 2.0 badge, FAQ, and footer agree with `LICENSE`, `NOTICE.md`, and manifest metadata |
| CLI/MCP claims | ✓ | Optional CLI and shipped local stdio MCP wrapper are described accurately |
| Dashboard image | ✓ | README points to the committed `checkyourself-dogfood-dashboard-live-20260612.png` |
| Hype words and filler | ✓ | Existing receipt recorded 0 for the checked deslop patterns |
| README example accuracy | ✓ | Existing receipt recorded the score and finding-severity corrections |

**README gate: PASS.**

## Public validation receipt

- `python3 tools/validate_public.py` exits 1 for the two known
  `_retrofit-2026-09-04/` markdown links listed in the dogfood recheck report.
- `python3 -m pytest tests/ -q` records **89 passed, 53 subtests passed, 1
  failed**, with the same known baseline cause.

Gate: **PASS WITH KNOWN BASELINE** — W8 product claims and the committed
dashboard asset agree; the remaining public-validator failure is confined to
orchestrator-owned retrofit markdown.
