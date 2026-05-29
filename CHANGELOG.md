# Changelog

## 1.4.0

- Added public repository validation with `tools/validate_public.py`.
- Added GitHub Actions validation for public repo health.
- Made the dashboard path explicit: CSS-only by default, advanced data-template only when requested or approved.
- Aligned the release boundary around the root public product plus private Creator Kit sidecar.
- Updated manifest and launch metadata for the public-ready repo shape.


## 1.3.0

- Clarified that CheckYourself performs a complete diagnostic and creates a complete remediation backlog.
- Added user-facing workflow diagram with no internal process leak.
- Added optional HTML/CSS dashboard mode and dashboard-data flow.
- Added token-efficiency guidance: dashboard off by default, advanced context loaded only when relevant.
- Added ICM-style context routing with stage-level `CONTEXT.md` files and output handoff folders.


## 1.2.0

- Added optional human-readable HTML/CSS dashboard mode.
- Added token-efficiency and progressive context-loading rules.
- Added user-facing workflow diagram with no internal process leak.
- Reinforced that the first approval batch is a safe starting batch, not the whole remediation scope.


## 1.1.0

- Clarified that CheckYourself must produce a complete remediation backlog, not just a small first approval batch.
- Renamed the beginner action list to “safest first approval batch.”
- Added a resolution policy: every finding must be fixed, accepted as risk, deferred with reason/date, or marked not applicable with evidence.
- Updated report schema with `remediation_backlog` and `first_approval_batch`.


## 1.0.0 — 2026-05-29

Initial public version of CheckYourself.

Includes:

- beginner prompt mode;
- folder-based diagnostic context;
- Production Reality Score;
- P0/P1/P2/P3 risk taxonomy;
- approval-based guided fix mode;
- bespoke learning-plan generator;
- full advanced production-hardening capability stack;
