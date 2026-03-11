# Database Notes

- The initial schema lives in `schema_v1.sql`.
- Keep schema evolution files in this directory as incremental additions rather than replacing the original reference schema.
- Application code should treat the current schema as the source of truth until migrations are introduced.
