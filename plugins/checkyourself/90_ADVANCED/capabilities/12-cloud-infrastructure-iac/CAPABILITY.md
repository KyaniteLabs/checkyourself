---
id: prodhardening.cloud_infrastructure_iac
name: cloud-infrastructure-iac
version: 1.0.0
status: stable
layer: "12 Cloud & Compute"
summary: "Design cloud infrastructure, networking, IAM, compute, storage, policy-as-code, cost controls, and IaC workflows."
description: "Use this capability for cloud architecture, IaC, Terraform/OpenTofu/Pulumi, Kubernetes, networking, VPC/VNet, IAM, compute, storage, managed databases, queues, cost controls, policy-as-code, drift detection, and infrastructure review."
activation:
  explicit_triggers:
    - cloud
    - infrastructure
    - IaC
    - Terraform
    - OpenTofu
    - Pulumi
    - Kubernetes
    - K8s
    - VPC
    - network
    - IAM
    - compute
    - storage
    - managed database
    - queue
    - cost
    - drift
    - policy-as-code
inputs:
  - architecture diagram
  - IaC files
  - cloud accounts/projects
  - network topology
  - IAM policy
  - cost constraints
  - compliance constraints
outputs:
  - cloud architecture
  - IaC review
  - network/IAM plan
  - policy-as-code checks
  - cost and resilience review
related_capabilities:
  - prodhardening.ci_cd_supply_chain
  - prodhardening.hosting_deployment_release
  - prodhardening.scaling_load_resilience
---
# Capability: cloud-infrastructure-iac
Design cloud infrastructure, networking, IAM, compute, storage, policy-as-code, cost controls, and IaC workflows.
## Operating contract

Act as a production hardening specialist for **12 Cloud & Compute**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for cloud architecture, IaC, Terraform/OpenTofu/Pulumi, Kubernetes, networking, VPC/VNet, IAM, compute, storage, managed databases, queues, cost controls, policy-as-code, drift detection, and infrastructure review.
## Inputs to request or inspect
- architecture diagram
- IaC files
- cloud accounts/projects
- network topology
- IAM policy
- cost constraints
- compliance constraints

## Work protocol
1. Translate application requirements into compute, network, storage, identity, observability, and recovery primitives.
2. Use IaC for reproducibility; review plans before apply and treat generated plans as security-sensitive artifacts.
3. Design network boundaries with explicit ingress/egress, private connectivity where appropriate, and least privilege identity flows.
4. Apply policy-as-code for public exposure, encryption, logging, backups, tags, region constraints, and prohibited resource classes.
5. Estimate cost drivers and define budgets, alerts, quotas, and cleanup routines for ephemeral environments.
6. Plan drift detection, state locking, secrets handling, and break-glass access.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- Infrastructure changes are reviewable as code and backed by plan output.
- No public exposure, wildcard permissions, or unencrypted storage exists without documented exception.
- State files, secrets, and credentials are protected separately from source code.
- Costs are bounded with budgets/alerts and environment cleanup rules.
- Critical infrastructure has backup, recovery, and observability controls.

## Anti-patterns to block
- Do not apply infrastructure changes from an unreviewed or model-generated plan.
- Do not put secrets in IaC variables, state, or logs without protected storage.
- Do not create broad IAM permissions to “make the deploy work”.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.ci_cd_supply_chain` when its layer is implicated by the findings.
- Consider `prodhardening.hosting_deployment_release` when its layer is implicated by the findings.
- Consider `prodhardening.scaling_load_resilience` when its layer is implicated by the findings.

## Examples
**Prompt:** “Review this Terraform plan.”

**Expected handling:** Check blast radius, public exposure, IAM, encryption, backups, tags, cost, drift, and rollback.

**Prompt:** “Design AWS/GCP/Azure infrastructure for this app.”

**Expected handling:** Return vendor-neutral primitives first, then map to specific cloud services if requested.

## References to load on demand
- `../../references/cloud-iac-hardening.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `../../templates/risk-register.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
