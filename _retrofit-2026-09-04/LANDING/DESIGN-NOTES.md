# CheckYourself landing page — design notes

Date: 2026-09-05  
Artifact: `index.html` at the repository root  
Scope: one self-contained, static GitHub Pages landing page; no external assets, fonts, scripts, or network calls.

## Direction snapshot

Build state: `committed-by-brief` for this executor handoff. The product brief supplied
the audience, job, factual register, and dark-first constraint; those are the authority for
the following inferred design decisions.

> Audit console meets editorial field note: a dark-first, left-anchored narrative with a
> lime evidence signal, serif claim-making type, mono verification labels, and one
> memorable proof trace that makes “done” visible as a sequence of receipts.

## Design-system interview — nine dimensions

| Dimension | Evidence | Decision | Consequence in the build |
| --- | --- | --- | --- |
| `reference` | Product is completion evidence for AI-built apps; audience has just heard “done” | Audit console + editorial field note | Rule lines, mono labels, restrained surfaces, and a readable narrative rather than a SaaS dashboard clone |
| `personality` | The product promises proof, reports unknowns, and avoids guarantees | Calmly exacting | Short declarative copy, visible caveats, no hype metrics, no celebratory “certified” language |
| `aesthetic` | Evidence is a sequence of observed and executed checks | Instrumental / tactile | Exposed grid lines, command line, numbered trace, squared controls, and one soft raised surface |
| `type` | Developer scanning plus a 30-second human read; no webfont or network dependency | Serif display + system sans body + mono labels | Georgia-family display face carries the promise; sans carries body reading; mono carries commands/statuses; `--measure: 66ch` |
| `color_mode` | Dark-first requirement; evidence needs a clear positive signal and a separate caveat signal | Near-black green ground, acid-lime primary, amber unproven state; dark, light, contrast themes | Semantic tokens remap per theme; status meaning is paired with words, not color alone |
| `density_shape` | The first screen needs breathing room; the trace needs compact scanability | Spacious shell, compact trace; 8px controls, 20px cards; low elevation | Section clamp is 56–112px; trace rows are 56.8px minimum; tags alone use pill radius |
| `structure_rhythm` | Product journey is install → audit → execute → score/learn | Asymmetric split hero; syncopated sections | Hero offsets the proof panel; proof is a quote split; process is a rail; coverage is a list panel; boundary is a callout band; install is a command card |
| `signature` | The core promise is turning a claim into evidence | Numbered proof trace | The hero’s “example output” visibly moves from read → execute → map → report unproven |
| `imagery_iconography` | No approved image library is needed to explain the product; external assets are prohibited | No imagery; inline CSS evidence diagram; check-mark mark | The console is diagrammatic and labelled, not decorative stock art; the mark is an accessible text check |

Optional motion decision: quiet hover lift and theme transitions only. The page remains
fully legible without motion; `prefers-reduced-motion: reduce` removes the lift and the
hero panel rotation and collapses transition durations.

## Refusals

- No indigo-to-violet gradient, glass panel, or floating blob.
- No centered hero followed by three equal feature cards.
- No pill-shaped text CTA; the pill token is reserved for tool tags.
- No fabricated customer proof, certification language, score example, or guarantee.
- No external imagery or font request that would add a network dependency to a local-first product.

## Token contract and measured values

The token source of truth is the `:root` block in `index.html`; component selectors use
semantic color roles. Primitive ramps use OKLCH, with an `@supports not (color: oklch())`
sRGB fallback for the semantic roles.

### Color

- Brand hue: 116° lime-green, used only for the primary action, positive trace states,
  focus, and the wordmark mark.
- Accent hue: 72° amber, used only for caveat / unproven states and the boundary rule.
- Neutral hue: 160° green-tinted charcoal; the light theme uses a warm 105° paper ground.
- Dark is not an inversion of light: dark surfaces step upward from `--color-bg` to
  `--color-surface-3`; light surfaces step downward from the paper ground.
- Numeric contrast audit below uses OKLCH-to-sRGB conversion with gamut clipping and the
  WCAG 2.x relative-luminance formula. Thresholds: 4.5:1 body text, 3:1 large text/UI.

| Theme | Pair | Measured ratio | Use |
| --- | --- | ---: | --- |
| Dark | text / background | 18.77:1 | body and headings |
| Dark | muted / background | 10.02:1 | secondary reading |
| Dark | text / surface 1 | 17.37:1 | console and panels |
| Dark | primary ink / primary | 8.97:1 | primary button |
| Dark | accent ink / accent | 9.82:1 | future accent fill contract |
| Dark | border / background | 3.08:1 | visible UI boundaries |
| Light | text / background | 16.78:1 | body and headings |
| Light | muted / background | 8.82:1 | secondary reading |
| Light | text / surface 1 | 15.36:1 | panels |
| Light | primary ink / primary | 7.33:1 | primary button |
| Light | accent ink / accent | 7.82:1 | future accent fill contract |
| Light | border / background | 3.62:1 | visible UI boundaries |
| Contrast | text / background | 20.20:1 | body and headings |
| Contrast | muted / background | 15.97:1 | secondary reading |
| Contrast | text / surface 1 | 19.71:1 | panels |
| Contrast | primary ink / primary | 13.95:1 | primary button |
| Contrast | accent ink / accent | 13.70:1 | future accent fill contract |
| Contrast | border / background | 8.45:1 | visible UI boundaries |

The page pairs status colors with text (`observed`, `executed`, `scoped`, `visible`) and
uses the contrast theme plus `forced-colors: active` cooperation for higher-contrast
environments. The final browser audit remains a required rendered verification gate.

### Type

| Role | Token / value | Job |
| --- | --- | --- |
| Display | `--step-5: clamp(3.3rem, 2.35rem + 5.5vw, 6.35rem)` | hero promise; max width 10.5ch |
| Section heading | `--step-3: clamp(2rem, 1.55rem + 2.2vw, 3.24rem)` | section hierarchy |
| Body | `--step-0: clamp(.98rem, .94rem + .18vw, 1.08rem)` | sustained reading |
| Label | `--step--2: clamp(.72rem, .7rem + .08vw, .78rem)` | metadata and status; never the only carrier of meaning |
| Reading measure | `--measure: 66ch`; local ledes 43–55ch | prevents long-line fatigue and choppy narrow copy |
| Font loading | system/local stacks only; no preload or remote request | avoids layout shift and preserves local-first behavior |

### Spacing and shape

The shared ladder is `4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96px`, represented by
`--space-1` through `--space-9`. Chapter rhythm is
`--space-section: clamp(3.5rem, 2rem + 5vw, 7rem)` = 56–112px across the supported range.

| Relationship | Token / measured value | Example |
| --- | --- | --- |
| Attachment | `--space-1` / 4px | signal dot to label |
| Control | `--space-2` or `--space-3` / 8–12px | button padding and tag gaps |
| Task | `--space-4` / 16px | command inset, copy groups |
| Group | `--space-5` / 24px | trace/heading relationships |
| Region | `--space-6` to `--space-8` / 32–64px | layout separation |
| Chapter | `--space-section` / 56–112px | section boundaries |

`--radius-control` is 8px; `--radius-card` is 20px; `--radius-pill` is 9999px and appears
only on compatible-tool tags. Shadows are limited to the proof and command surfaces so
the exposed rules remain the visual anchor.

## Section-to-skill map

| Section / element | Skills that drove it | Intentional result |
| --- | --- | --- |
| Header + theme switcher | `theming`, `component-states`, `a11y-pass` | Native buttons, visible `aria-pressed`, 36px targets, focus-visible ring, persistent user choice |
| Hero + proof trace | `design-system-interview`, `art-direction`, `web-typography`, `humanize-copy` | No image dependency; the trace explains the product job without inventing output data |
| Principle bar | `color-system`, `theming`, `spacing-system` | Three short product principles with a non-color lime marker |
| Gap / proof section | `humanize-copy`, `deslop-ui`, `spacing-system` | Reframes “done” vs “ready” with a quote split instead of a feature-card grid |
| Audit loop | `responsive-layout`, `component-states`, `spacing-system` | Four-step editorial rail; content stacks in source order on narrow screens |
| Coverage panel | `color-system`, `responsive-layout`, `deslop-ui` | Unequal text-and-list treatment; 20 surfaces / 10 categories / 150+ tests stay source-bound |
| Boundary callout | `humanize-copy`, `theming`, `a11y-pass` | Quiet, customer-phrased limit: evidence is not a guarantee and unchecked work stays visible |
| Start command | `humanize-copy`, `component-states`, `responsive-layout` | Real CLI command, no fake “try demo” interaction, bounded reflow via `overflow-wrap` |

## Verification ledger

| Skill / check | Status | Evidence | Remaining gate |
| --- | --- | --- | --- |
| `design-system-interview` | PASS | Nine dimensions recorded above; the executor brief supplies explicit product, audience, and mode constraints | This is a headless inferred-system handoff, not a separate user interview |
| `color-system` | PASS / numeric | OKLCH ramps, semantic tokens, sRGB fallback, 18 contrast pairs measured above | Re-run the supplied rendered audit in a working browser |
| `web-typography` | PASS / source | Fluid scale, 66ch max measure, system/local font stacks, balanced headings | Confirm rendered wraps at 390px and 200–400% zoom |
| `spacing-system` | PASS / source | One 4px ladder, role map, 56–112px section rhythm, no arbitrary margin cascade | Confirm computed spacing in browser |
| `theming` | PASS / source | Dark/light/contrast semantic remaps, early localStorage resolution, color-scheme, forced-colors rule | Confirm cold-load preference and each theme in browser |
| `responsive-layout` | PASS / source; render pending | Intrinsic grids, `minmax(0, ...)`, content-led 58rem/44rem breakpoints, 320px guard | Browser must confirm no horizontal overflow at 390/768/1280 and zoom |
| `component-states` | PASS / source | Hover, active, `:focus-visible`, selected theme, keyboard-native buttons, reduced motion | Browser keyboard trace |
| `art-direction` | PASS | No external asset; inline CSS diagram has caption and informative labels | None for this no-imagery direction |
| `humanize-copy` | PASS | Copy uses exact brief facts, concrete verbs, bounded claim, and explicit score boundary | None identified |
| `deslop-ui` | PASS / source | No purple gradient, no pill CTA, no centered three-card skeleton; proof trace is the signature | Browser computed tell audit |
| `a11y-pass` | HOLD | Source has landmarks, one h1, native controls, skip link, focus style, theme labels, and 24px+ targets by CSS intent | Supplied `audit.js` could not execute because no working headless browser was available in this environment |
| `tastecheck-pass` | HOLD | Artifact and notes exist; no external assets; JavaScript syntax passes; Python/BeautifulSoup structure check passes | Required cold-load, rendered width, keyboard, reduced-motion, and supplied browser audits |

## Verification command notes

- `td usage --new-session` was attempted as required, but this worktree has no initialized
  `td` database; no task state was created.
- Both inline page scripts pass `node --input-type=module --check` extraction.
- A structural parse confirms one `h1`, five `h2` headings, six `h3` headings, `main`,
  `nav`, `footer`, three `data-test^="theme-"` controls, zero images, and zero external
  asset URLs.
- The installed Playwright CLI found the system Chrome binary but Chrome aborts before
  opening a headless page/debug endpoint in this managed runtime. No network or install was
  used to work around it. This is an environment evidence gap, not a claim that the page
  has passed the rendered gate.

## Handoff

Files delivered:

- `index.html` — self-contained public landing page at the repository root.
- `_retrofit-2026-09-04/LANDING/DESIGN-NOTES.md` — direction, token contract, measured palette values, skill map, and fail-closed verification ledger.

No Git commit or push was performed.
