---
id: prodhardening.frontend_experience
name: frontend-experience
version: 1.0.0
status: stable
layer: "02 Frontend"
summary: "Build and harden user interfaces for accessibility, performance, resilience, and secure client behavior."
description: "Use this capability for UI architecture, frontend performance, accessibility, routing guards, forms, client state, design-system integration, browser security boundaries, and user-facing AI interfaces. Trigger on React, Vue, Angular, Svelte, components, UI, a11y, WCAG, Core Web Vitals, forms, routing, lazy loading, bundle size, hydration, or client errors."
activation:
  explicit_triggers:
    - frontend
    - UI
    - component
    - React
    - Vue
    - Angular
    - Svelte
    - a11y
    - WCAG
    - form
    - routing
    - lazy loading
    - bundle
    - hydration
    - Core Web Vitals
inputs:
  - designs
  - component code
  - routes
  - state model
  - API contracts
  - browser errors
  - performance traces
outputs:
  - frontend implementation plan
  - component changes
  - accessibility checklist
  - performance budget
  - client-side security review
related_capabilities:
  - prodhardening.api_backend_services
  - prodhardening.security_privacy_threat_modeling
  - prodhardening.observability_sre_incident_response
---
# frontend-experience
Build and harden user interfaces for accessibility, performance, resilience, and secure client behavior.
## Operating contract

Act as a production hardening specialist for **02 Frontend**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for UI architecture, frontend performance, accessibility, routing guards, forms, client state, design-system integration, browser security boundaries, and user-facing AI interfaces. Trigger on React, Vue, Angular, Svelte, components, UI, a11y, WCAG, Core Web Vitals, forms, routing, lazy loading, bundle size, hydration, or client errors.
## Inputs to request or inspect
- designs
- component code
- routes
- state model
- API contracts
- browser errors
- performance traces

## Work protocol
1. Map UI work into pages, sections, widgets, primitives, layouts, hooks, and shared state boundaries.
2. Prefer typed contracts at API boundaries and schema-validated form input before mutation calls.
3. Design for loading, empty, error, offline, partial-data, and permission-denied states before styling polish.
4. Enforce accessibility through semantic HTML, keyboard paths, focus management, labels, contrast, and screen-reader behavior.
5. Budget performance by route: initial payload, lazy-loaded chunks, expensive renders, image strategy, hydration cost, and network waterfalls.
6. Treat the browser as untrusted. Never rely on client-side route guards as the only authorization control.
7. For AI/RAG interfaces, expose citations, uncertainty, feedback controls, and safe failure states.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Critical flows pass keyboard-only and screen-reader sanity checks.
- Every protected route also has server-side authorization enforcement.
- Forms validate on client for UX and on server for security.
- Performance budgets are stated and measurable with reproducible tools.
- Errors are user-actionable and instrumented with correlation identifiers where possible.

## Anti-patterns to block
- Do not hide authorization decisions inside the UI.
- Do not add memoization before measuring render bottlenecks.
- Do not ship a happy-path-only interface with no empty/error/loading states.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.api_backend_services` when its layer is implicated by the findings.
- Consider `prodhardening.security_privacy_threat_modeling` when its layer is implicated by the findings.
- Consider `prodhardening.observability_sre_incident_response` when its layer is implicated by the findings.

## Examples
**Prompt:** “Review this React dashboard for production readiness.”

**Expected handling:** Check component boundaries, data fetching, route guards, a11y, render cost, error states, and telemetry.

**Prompt:** “Build the upload form.”

**Expected handling:** Specify validation, disabled/loading states, accessible labels, error handling, server contract, and tests.

## References to load on demand
- `../../references/frontend-hardening.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `../../references/standards-baseline.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
