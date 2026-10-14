---
id: prodhardening.identity_access_control
name: identity-access-control
version: 1.0.0
status: stable
layer: "05 Auth & Permissions"
summary: "Design and harden authentication, authorization, sessions, tokens, identity federation, and permission models."
description: "Use this capability for login, signup, session management, OAuth/OIDC, SSO, JWT, cookies, MFA, RBAC, ABAC, ReBAC, permission checks, service identities, and access reviews. Trigger on auth, login, signup, token, JWT, OAuth, OIDC, SSO, session, cookie, role, permission, MFA, 2FA, tenant access, or service account."
activation:
  explicit_triggers:
    - auth
    - authentication
    - authorization
    - login
    - signup
    - JWT
    - OAuth
    - OIDC
    - SSO
    - session
    - cookie
    - role
    - permission
    - RBAC
    - ABAC
    - MFA
    - service account
inputs:
  - user flows
  - identity provider constraints
  - permission model
  - API routes
  - data model
  - threat model
outputs:
  - identity architecture
  - permission model
  - auth flow review
  - policy checks
  - test plan
  - security controls
related_capabilities:
  - prodhardening.multitenancy_rls_isolation
  - prodhardening.security_privacy_threat_modeling
  - prodhardening.api_backend_services
---
# identity-access-control
Design and harden authentication, authorization, sessions, tokens, identity federation, and permission models.
## Operating contract

Act as a production hardening specialist for **05 Auth & Permissions**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for login, signup, session management, OAuth/OIDC, SSO, JWT, cookies, MFA, RBAC, ABAC, ReBAC, permission checks, service identities, and access reviews. Trigger on auth, login, signup, token, JWT, OAuth, OIDC, SSO, session, cookie, role, permission, MFA, 2FA, tenant access, or service account.
## Inputs to request or inspect
- user flows
- identity provider constraints
- permission model
- API routes
- data model
- threat model

## Work protocol
1. Separate authentication from authorization. Confirm identity once; authorize every sensitive action.
2. Choose sessions, tokens, and federation based on app type, clients, revocation needs, threat model, and operational maturity.
3. Model permissions around resources and actions; roles are conveniences, not the authorization source of truth.
4. Enforce server-side authorization at API/service/data boundaries and test negative cases explicitly.
5. Protect tokens and cookies with secure flags, short lifetimes, rotation strategy, CSRF protection where relevant, and revocation paths.
6. Define administrative and service-account privileges with least privilege, auditability, and break-glass controls.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Every protected route and mutating API has an authorization check independent of frontend UI state.
- Every privileged role has a documented permission set, owner, review cadence, and audit trail.
- Token storage and cookie settings match the threat model and client type.
- Password, MFA, recovery, and email verification flows avoid account enumeration and replay problems.
- Service identities have scoped credentials, rotation, and no broad default permissions.

## Anti-patterns to block
- Do not treat role names as hard-coded authorization logic scattered across code.
- Do not store long-lived tokens in unsafe browser storage without justification.
- Do not let admin bypasses silently override tenant or privacy boundaries.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.multitenancy_rls_isolation` when its layer is implicated by the findings.
- Consider `prodhardening.security_privacy_threat_modeling` when its layer is implicated by the findings.
- Consider `prodhardening.api_backend_services` when its layer is implicated by the findings.

## Examples
**Prompt:** “Add RBAC to the app.”

**Expected handling:** Return resources/actions, roles, policy checks, data model changes, negative tests, and audit events.

**Prompt:** “Is JWT or sessions better here?”

**Expected handling:** Compare revocation, clients, storage, CSRF/XSS exposure, scaling, and operational requirements.

## References to load on demand
- `../../references/security-standards.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `../../references/multitenancy-rls.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
