---
id: prodhardening.ci_cd_supply_chain
name: ci-cd-supply-chain
version: 1.0.0
status: stable
layer: "10 CI/CD & Version Control"
summary: "Harden repositories, pull requests, CI/CD pipelines, releases, provenance, dependencies, and artifact integrity."
description: "Use this capability for Git workflow, pull request policy, branch protection, CI/CD, build pipelines, release automation, dependency management, SBOM, provenance, SLSA, signing, container scanning, lockfiles, and supply-chain security. Trigger on CI, CD, pipeline, Git, branch, PR, release, dependency, SBOM, provenance, SLSA, signing, artifact, container scan, or versioning."
activation:
  explicit_triggers:
    - CI
    - CD
    - pipeline
    - Git
    - branch
    - PR
    - release
    - dependency
    - SBOM
    - provenance
    - SLSA
    - signing
    - artifact
    - container scan
    - versioning
    - lockfile
inputs:
  - repository settings
  - workflow files
  - build scripts
  - dependency manifests
  - release process
  - container files
outputs:
  - pipeline design
  - repo governance plan
  - supply-chain controls
  - release checklist
  - artifact verification plan
related_capabilities:
  - prodhardening.testing_quality_engineering
  - prodhardening.security_privacy_threat_modeling
  - prodhardening.hosting_deployment_release
---
# ci-cd-supply-chain
Harden repositories, pull requests, CI/CD pipelines, releases, provenance, dependencies, and artifact integrity.
## Operating contract

Act as a production hardening specialist for **10 CI/CD & Version Control**. Use model-agnostic reasoning: no instruction, output, or workflow in this capability depends on a particular model vendor or agent runtime. Prefer deterministic evidence over persuasive prose. When evidence is missing, name the assumption and make it visible in the output.
## When to activate
Use this capability for Git workflow, pull request policy, branch protection, CI/CD, build pipelines, release automation, dependency management, SBOM, provenance, SLSA, signing, container scanning, lockfiles, and supply-chain security. Trigger on CI, CD, pipeline, Git, branch, PR, release, dependency, SBOM, provenance, SLSA, signing, artifact, container scan, or versioning.
## Inputs to request or inspect
- repository settings
- workflow files
- build scripts
- dependency manifests
- release process
- container files

## Work protocol
1. Map the path from source to running artifact: branch, review, build, test, package, sign, publish, deploy, and rollback.
2. Enforce least privilege in CI tokens and isolate build, test, deploy, and release permissions.
3. Make security gates deterministic: dependency scan, secret scan, SAST, IaC scan, container scan, SBOM generation, and provenance where applicable.
4. Use protected branches, required reviews, status checks, signed commits/tags where appropriate, and clear exception handling.
5. Pin dependencies or lock versions with update automation, vulnerability triage, and reproducible build intent.
6. Promote artifacts across environments rather than rebuilding separately when release integrity matters.

## Required output format

Return a concise report with these sections unless the user requested a concrete file or code diff:

1. **Scope interpreted** — what is in and out.
2. **Findings / decisions** — ordered by production risk, not by discovery order.
3. **Recommended actions** — owner-ready tasks with priority and rationale.
4. **Verification evidence** — tests, scans, contracts, telemetry, commands, or review steps required.
5. **Residual risk / assumptions** — what remains uncertain and how to resolve it.
6. **Hand-offs** — other capabilities that should review the work.
## Verification gates
- No production deployment can occur from unreviewed or unverified source.
- CI secrets are scoped, rotated, and unavailable to untrusted fork/PR contexts.
- Build artifacts have traceability to source, dependencies, build workflow, and release approval.
- Dependency updates include vulnerability, license, and compatibility review proportional to risk.
- Rollback is tested or documented for every release path.

## Anti-patterns to block
- Do not grant broad cloud/admin credentials to general CI jobs.
- Do not rebuild a different artifact for production than the one tested in staging without reason.
- Do not let optional scan warnings become invisible permanent noise.

## Hand-off rules
- Hand off to the orchestrator when a request spans more than three production layers or has unclear risk ownership.
- Consider `prodhardening.testing_quality_engineering` when its layer is implicated by the findings.
- Consider `prodhardening.security_privacy_threat_modeling` when its layer is implicated by the findings.
- Consider `prodhardening.hosting_deployment_release` when its layer is implicated by the findings.

## Examples
**Prompt:** “Make this repo release-ready.”

**Expected handling:** Return branch protections, CI gates, scans, artifact provenance, SBOM, and release process.

**Prompt:** “Review this GitHub Actions workflow.”

**Expected handling:** Check token permissions, trigger safety, secret exposure, caching risk, artifact integrity, and deploy gates.

## References to load on demand
- `references/supply-chain-ci-cd.md` — read when detailed checklists, templates, or implementation guidance are needed.
- `references/security-standards.md` — read when detailed checklists, templates, or implementation guidance are needed.

## Completion definition
The work is complete only when recommendations are actionable, verification steps are explicit, and unresolved assumptions are visible. Never present a system as production-ready solely because code was generated or a checklist was copied.
