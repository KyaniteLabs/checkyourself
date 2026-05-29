# Dashboard Data Fields

Use this compact data shape before generating HTML.

```yaml
project:
  name:
  detected_stack:
  score:
  previous_score:
  ship_status:
  generated_at:
summary:
  p0:
  p1:
  p2:
  p3:
  open:
  fixed:
  deferred:
  accepted_risk:
  not_applicable:
coverage:
  - surface:
    status: pass | finding | unknown | not_applicable
    note:
findings:
  - id:
    severity:
    title:
    plain_english_risk:
    evidence:
    status:
    recommended_fix:
backlog:
  - order:
    finding_id:
    fix_summary:
    status:
    verification:
    rollback:
approval_batch:
  - finding_id:
    approval_question:
learning_plan:
  inferred_level:
  next_concepts:
    - concept:
      why_it_matters:
      practice_task:
```
