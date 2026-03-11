# Database Workflow

PropertyAdvisor is not shipping a managed database in this repo yet, but the local development workflow now treats `db/schema_v1.sql` as the canonical schema reference.

## Local bootstrap

1. Create a local Postgres database.
2. Export `DATABASE_URL`.
3. Apply the schema with the helper script:

```bash
export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/propertyadvisor'
./db/scripts/apply_schema.sh
```

## Notes

- The script only applies the checked-in local schema file; it does not deploy anywhere externally.
- Keep future schema changes additive in `db/` until a migration tool is introduced.
- API and domain code should assume Postgres is the long-term source of truth, even while current endpoints are placeholder-backed.
