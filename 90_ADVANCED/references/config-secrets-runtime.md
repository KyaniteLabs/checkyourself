# Configuration, Secrets & Runtime Reference

## Configuration classes

| Class | Examples | Handling |
|---|---|---|
| Public config | public URL, feature display mode | Can be visible; validate format. |
| Secret | API key, database password, signing key | Store in managed secret system; never log. |
| Operational limit | max upload size, timeout | Validate at startup; monitor changes. |
| Feature flag | rollout, kill switch | Owner, expiry, telemetry, cleanup. |
| Deployment constant | region, service name | Define per environment; verify during smoke test. |

## Startup validation

Applications should fail closed on missing critical config rather than starting in an unsafe partial state.
