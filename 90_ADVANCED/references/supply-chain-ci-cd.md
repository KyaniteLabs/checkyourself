# CI/CD & Supply Chain Reference

## Pipeline stages

1. Source review and branch policy
2. Dependency installation from trusted registries
3. Secret scan
4. Type/lint/static checks
5. Unit/integration/contract tests
6. Security/dependency/container/IaC scans
7. Build artifact generation
8. SBOM and provenance generation where required
9. Staging deploy and smoke test
10. Production approval and progressive release
11. Post-deploy verification

## CI token safety

- Use least privilege
- Separate read/build/test/deploy permissions
- Restrict secrets for untrusted PRs
- Avoid long-lived broad credentials
- Log release approvals and artifact identity
