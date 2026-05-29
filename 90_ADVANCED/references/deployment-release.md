# Deployment & Release Reference

## Safe deployment checklist

- Artifact built once and promoted
- Environment variables validated
- Database compatibility confirmed
- Health checks and smoke tests ready
- Observability dashboards open
- Rollback/roll-forward documented
- Support and incident channel identified
- Feature flags and kill switches verified

## Deployment strategies

- Rolling: simple, requires backward compatibility.
- Blue-green: fast rollback, higher duplicate environment cost.
- Canary: low blast radius, requires traffic routing and telemetry.
- Feature flag rollout: controls behavior independently from artifact deploy.
