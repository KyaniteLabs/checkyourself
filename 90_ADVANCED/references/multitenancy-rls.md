# Multi-Tenancy and Row-Level Security Reference

## Tenant isolation design

Classify every data location:

- Primary database rows
- Join tables
- Object/blob storage
- Search indexes
- Caches
- Queues and jobs
- Analytics events
- Logs and traces
- Exports and reports
- Support/admin tools

## PostgreSQL RLS pattern

Use transaction-scoped tenant context and non-bypass application roles where possible.

```sql
BEGIN;
SET LOCAL app.current_tenant = '00000000-0000-0000-0000-000000000000';
-- tenant-scoped queries
COMMIT;
```

Example policy shape:

```sql
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON invoices
  FOR ALL TO app_user
  USING (tenant_id = current_setting('app.current_tenant')::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);
```

## Negative tests

- Tenant A cannot list Tenant B records
- Tenant A cannot fetch by guessed ID
- Tenant A cannot update/delete Tenant B records
- Tenant A cannot create records assigned to Tenant B
- Aggregates do not include another tenant
- Background jobs preserve tenant context
- Cache/search/blob paths cannot cross tenants
