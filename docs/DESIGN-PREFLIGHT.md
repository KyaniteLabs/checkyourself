# CheckYourself design preflight

This file records why the CheckYourself icon looks the way it does. Read it before changing any identity asset.

## 1. Purpose

CheckYourself runs local challenges against the work an AI coding assistant claims it did. It records evidence and exposes risks before an app ships. The user's outcome: know what is actually true about the app before launch.

## 2. Title ↔ stone ↔ purpose

| Element | Choice | Evidence class |
|---|---|---|
| Form | The "Return Frame": an open square frame whose arrow points back at the core. Claimed work returns to be checked against evidence | Product fit (our metaphor); eye-gate history (r7, r8) |
| Frame | Black tourmaline | Earlier Check Yourself rounds; **Assumption:** Simon has not confirmed the frame stone separately from the 6B pick |
| Core | Smoky quartz, with a measuring gauge and target engraved in it | Simon approved 6B (smoky quartz core), 2026-11-10 |

## 3. Rejected metaphors

- Malachite core inside black tourmaline: Simon called it "too jarring".
- Teal and deep-green cores (r3 and r4 alternates): not picked.
- Monotone all-tourmaline versions (r7 and r8): "too monotone".

## 4. Material reference

- Smoky quartz is brown-to-grey quartz; the colour comes from natural irradiation of quartz containing trace aluminium. Source: [Wikipedia, Smoky quartz](https://en.wikipedia.org/wiki/Smoky_quartz).
- Black tourmaline (schorl) is the iron-rich tourmaline, with striated prismatic crystals. Source: [Wikipedia, Schorl](https://en.wikipedia.org/wiki/Schorl).
- Retail associations were not used as a reason for either stone.
- Render: eye-gate round 3 `checkyourself-smoky-v1` (shown as 6B), source sha256 `db79d0abc3ed…`.

## 5. Family icon law and form

One hero object, centred at about 80% fill, transparent background, no tile, glow or cast shadow.

## 6. Typography

The KyaniteLabs lockup is Chakra Petch Bold 700 uppercase for the wordmark, with Medium 500 for "by KyaniteLabs". No lockup ships in this change.

## 7. Platform conventions

| Surface | File |
|---|---|
| README hero | `branding/checkyourself-512.png` at 128 px |
| Favicon-sized | `branding/checkyourself-32.png`. Not wired into `index.html` yet; that is a follow-up |

## 8. UI colour

**Assumption:** no UI colour change. The existing site palette stands.
