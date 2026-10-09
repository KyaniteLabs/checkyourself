---
id: prodhardening.observability_sre_incident_response
name: observability-sre-incident-response
version: 1.0.0
status: stable
layer: "15 Error Tracking, Logs & Incidents"
summary: "Instrument systems with logs, metrics, traces, alerts, dashboards, runbooks, incident response, and root-cause analysis."
description: "Use this capability for logging, metrics, traces, OpenTelemetry, error tracking, correlation IDs, dashboards, alerts, SLO burn alerts, runbooks, incident triage, root-cause analysis, postmortems, and on-call readiness."
activation:
  explicit_triggers:
    - logs
    - logging
    - metrics
    - traces
    - OpenTelemetry
    - observability
    - error tracking
    - correlation ID
    - dashboard
    - alert
    - SLO
    - incident
    - RCA
    - postmortem
    - on-call
    - runbook
inputs:
  - service list
  - SLOs
  - logs/metrics/traces
  - alerts
  - dashboards
  - incident notes
  - deployment history
outputs:
  - instrumentation plan
  - observability review
  - alert design
  - incident analysis
  - runbook
  - postmortem
related_capabilities:
  - prodhardening.availability_recovery_continuity
  - prodhardening.performance_caching_rate_limits
  - prodhardening.ai_agent_rag_governance
---
# Capability: observability-sre-incident-response
Instrument systems with logs, metrics, traces, alerts, dashboards, runbooks, incident response, and root-cause analysis.
## Operating contract

Act as a production hardening specialist for **15 Error Tracking, Logs & Incidents**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for logging, metrics, traces, OpenTelemetry, error tracking, correlation IDs, dashboards, alerts, SLO burn alerts, runbooks, incident triage, root-cause analysis, postmortems, and on-call readiness.
## Inputs to request or inspect
- service list
- SLOs
- logs/metrics/traces
- alerts
- dashboards
- incident notes
- deployment history

## Work protocol
1. Start from user journeys and SLOs. Instrument what users care about before internal counters.
2. Use structured logs, metrics, traces, profiles where useful, and correlation/context propagation to connect signals.
3. Design alerts for actionable symptoms and burn rate, not every noisy threshold.
4. Create dashboards that answer: is it broken, who is affected, where is it broken, what changed, and what should we do?
5. During incidents, separate facts, hypotheses, actions, and unknowns. Timestamp decisions and preserve an audit trail.
6. Convert incidents into fixes: code, tests, dashboards, runbooks, ownership, and follow-up deadlines.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Every critical path emits enough telemetry to diagnose latency, errors, saturation, and dependency failures.
- Logs redact secrets/PII and include stable identifiers for correlation without exposing sensitive data.
- Alerts have owner, severity, runbook, user impact definition, and expected action.
- Postmortems identify contributing factors and systemic fixes rather than blame.
- Automated SRE actions are constrained by approval levels and risk gates.

## Anti-patterns to block
- Do not page humans for non-actionable noise.
- Do not log sensitive data to make debugging easier.
- Do not treat traces alone as a complete root-cause explanation without topology, deployments, and logs.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.availability_recovery_continuity` when its layer is implicated by the findings.
- Consider `prodhardening.performance_caching_rate_limits` when its layer is implicated by the findings.
- Consider `prodhardening.ai_agent_rag_governance` when its layer is implicated by the findings.

## Examples
**Prompt:** “Add observability to checkout.”

**Expected handling:** Return SLIs, metrics, spans, logs, dashboards, alerts, redaction, and runbook updates.

**Prompt:** “Analyze this incident.”

**Expected handling:** Construct timeline, facts, hypotheses, root cause, mitigation, follow-ups, and prevention gates.

## References to load on demand
- `../../references/observability-sre.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `../../templates/incident-report.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
