# Data Storage & Migration Hardening Reference

## Zero/low-downtime migration sequence

1. Expand schema with backward-compatible fields/tables.
2. Deploy code that can read/write old and new shapes.
3. Backfill safely in batches with observability and retry behavior.
4. Verify parity and performance.
5. Switch reads/writes to new path.
6. Contract old schema in a later release.

## Query review checklist

- Expected cardinality
- Index coverage
- Join strategy
- Sort/filter limits
- Transaction isolation and lock behavior
- Connection pool impact
- Timeout behavior
- Tenant/privacy scope

## Backup considerations

- Point-in-time recovery
- Encryption and access control
- Restore drill cadence
- Backup isolation from production compromise
- Retention and legal hold
- Deletion/anonymization behavior across backups
