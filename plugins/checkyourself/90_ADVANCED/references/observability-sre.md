# Observability & SRE Reference

## Telemetry requirements

- Logs: structured events with redaction and request correlation
- Metrics: request rate, error rate, duration, saturation, business counters
- Traces: critical request paths and dependency spans
- Profiles: resource hot spots when needed
- Events: deployments, feature flag changes, migrations, incidents

## Incident timeline structure

- Detection time
- User impact
- Facts observed
- Hypotheses considered
- Actions taken
- Mitigation time
- Recovery time
- Root/contributing causes
- Follow-up owners and dates
