---
id: prodhardening.ai_agent_rag_governance
name: ai-agent-rag-governance
version: 1.0.0
status: stable
layer: "17 AI/RAG & Agent Governance"
summary: "Harden AI features and AI coding workflows with evals, retrieval grounding, prompt-injection defenses, sandboxing, audit logs, and graded autonomy."
description: "Use this capability for AI features, RAG, citations, model-agnostic prompts, evals, hallucination reduction, prompt injection, tool use, agent sandboxes, policy gates, audit trails, autonomy levels, human approval, and AI-assisted coding governance."
activation:
  explicit_triggers:
    - AI
    - LLM
    - RAG
    - citation
    - retrieval
    - eval
    - hallucination
    - prompt injection
    - agent
    - tool use
    - sandbox
    - autonomy
    - human approval
    - model agnostic
    - coding agent
inputs:
  - AI use case
  - retrieval corpus
  - prompts
  - tools/actions
  - eval data
  - policy requirements
  - agent runtime
outputs:
  - AI feature hardening plan
  - RAG quality checklist
  - eval suite
  - tool safety policy
  - agent autonomy matrix
  - audit plan
related_capabilities:
  - prodhardening.security_privacy_threat_modeling
  - prodhardening.testing_quality_engineering
  - prodhardening.observability_sre_incident_response
---
# ai-agent-rag-governance
Harden AI features and AI coding workflows with evals, retrieval grounding, prompt-injection defenses, sandboxing, audit logs, and graded autonomy.
## Operating contract

Act as a production hardening specialist for **17 AI/RAG & Agent Governance**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for AI features, RAG, citations, model-agnostic prompts, evals, hallucination reduction, prompt injection, tool use, agent sandboxes, policy gates, audit trails, autonomy levels, human approval, and AI-assisted coding governance.
## Inputs to request or inspect
- AI use case
- retrieval corpus
- prompts
- tools/actions
- eval data
- policy requirements
- agent runtime

## Work protocol
1. Separate model behavior from deterministic controls. The model may propose; platform policy, schemas, tools, and tests enforce.
2. For RAG, evaluate retrieval quality, answer faithfulness, citation granularity, source freshness, access control, and user feedback loops.
3. Defend against prompt injection by isolating untrusted content, constraining tools, validating tool inputs, and never treating retrieved text as instruction authority.
4. Run coding agents in disposable, least-privilege sandboxes with network/filesystem/tool restrictions and auditable actions.
5. Grade autonomy by risk: read-only, advised, approved execution, and bounded autonomous execution only for pre-cleared reversible actions.
6. Use two-signal gating for remediations: trust in diagnosis plus risk/blast-radius limit. Either failure escalates to humans.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Every AI output that affects users or systems has a validation, review, or monitoring path proportional to harm.
- Every tool/action has schema validation, least privilege, audit logging, and explicit deny boundaries.
- RAG answers expose sources when claims depend on retrieval and enforce document access control before retrieval or generation.
- Agent-generated code goes through the same tests, scans, reviews, and deployment gates as human-written code.
- Autonomous actions are bounded, reversible, observable, and pre-approved by policy rather than prompt text.

## Anti-patterns to block
- Do not put vendor-specific instructions in the core capability pack.
- Do not rely on the model to remember safety policy instead of enforcing it in tools and workflow gates.
- Do not let an AI agent modify production without explicit autonomy level and risk gate.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.security_privacy_threat_modeling` when its layer is implicated by the findings.
- Consider `prodhardening.testing_quality_engineering` when its layer is implicated by the findings.
- Consider `prodhardening.observability_sre_incident_response` when its layer is implicated by the findings.

## Examples
**Prompt:** “Harden this RAG chatbot for production.”

**Expected handling:** Return retrieval/access/citation/eval/safety/monitoring controls and rollout gates.

**Prompt:** “Can coding agents self-heal incidents?”

**Expected handling:** Return an autonomy matrix, trust/risk gate, allowed actions, audit trail, and human escalation path.

## References to load on demand
- `references/ai-agent-rag-governance.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `templates/ai-eval-plan.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
