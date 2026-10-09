# Availability & Recovery Reference

## Availability concepts

- SLI: the measurement
- SLO: the target
- SLA: the external promise and consequence
- Error budget: how much unreliability is acceptable within the SLO window
- RTO: how quickly service must be restored
- RPO: how much data loss is acceptable

## Backup restore drill

1. Choose restore point
2. Restore into isolated environment
3. Verify schema and data integrity
4. Verify application can read restored data
5. Measure restore time and data loss
6. Update RTO/RPO evidence
7. Record defects and fixes
