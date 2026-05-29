# Dashboard Data Contract

Use `schemas/dashboard-data.schema.json` as the canonical validation contract.

The schema accepts two dashboard data shapes:

1. **Compact data mode** for agents that emit `app_name`, `findings`,
   `remediation_waves`, and `learning_priorities`.
2. **HTML-template mode** for the bundled templates that use `project`,
   `backlog`, and `learning_plan`.

Prefer compact data mode for new dashboard data. Use HTML-template mode when
replacing the JSON inside an existing template.

```yaml
app_name: ""
score: 0
confidence: "low|medium|high"
detected_stack: []
summary: ""
counts:
  P0: 0
  P1: 0
  P2: 0
  P3: 0
coverage:
  - surface: "Auth and permissions"
    status: "Pass|Finding|Unknown|N/A"
    evidence: "short evidence"
findings:
  - id: "P1-001"
    severity: "P1"
    title: ""
    plain_risk: ""
    evidence: ""
    status: "open|proposed|approved|fixed|verified|deferred|accepted-risk|not-applicable"
remediation_waves:
  - wave: "Wave 1"
    goal: ""
    items: []
next_approval: ""
learning_priorities:
  - concept: ""
    why: ""
```
