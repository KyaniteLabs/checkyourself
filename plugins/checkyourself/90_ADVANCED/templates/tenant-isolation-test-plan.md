# Tenant Isolation Test Plan

## Fixtures

- Tenant A
- Tenant B
- User A in Tenant A
- User B in Tenant B
- Admin/support roles

## Test cases

| Path | Expected result | Evidence |
|---|---|---|
| List records across tenants | Denied/filtered |  |
| Fetch guessed ID | Denied/not found |  |
| Update foreign tenant row | Denied |  |
| Create with foreign tenant_id | Denied |  |
| Aggregate reports | Scoped |  |
| Cache hit after tenant switch | Scoped |  |
| Background job | Scoped |  |
| Export | Scoped |  |
