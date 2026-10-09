# Cloud & IaC Hardening Reference

## IaC plan review

- Resources created, changed, destroyed
- Public ingress/egress changes
- IAM permission changes
- Encryption and key management
- Logging and monitoring
- Backup and recovery settings
- Cost impact
- Region/residency impact
- Drift and state safety

## Policy-as-code examples

- Block public object storage unless explicitly approved
- Require encryption at rest
- Require logs for load balancers and managed databases
- Restrict admin permissions
- Require tags/labels for owner and environment
- Block deletion protection changes for critical databases without approval
