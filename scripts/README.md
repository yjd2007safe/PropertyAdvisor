# Scripts

This folder is reserved for small local developer helpers.

Suggested bootstrap flow:

```bash
./scripts/bootstrap_backend.sh
./scripts/bootstrap_web.sh
```

Notes:

- `bootstrap_backend.sh` prefers a local `.venv`, but falls back to a user-site `pip3 install` if `python3-venv` is unavailable on the machine.
- `start_api.sh` runs the FastAPI app from `.venv` when present, otherwise via the system `python3`.
- `db/scripts/apply_schema.sh` applies the checked-in `db/schema_v1.sql` to a locally configured Postgres instance via `DATABASE_URL`.

Add scripts here only when they remove repeated local setup or data-prep work.
