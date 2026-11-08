# PostgreSQL dump kept in the repo

`7didan_backup.sql` is a plain-SQL export of the vector store
(`public."7didan_store"`, 431 rows including the `url` metadata) and the
`reporting` schema (`conversation_events` funnel events).

- Regenerate after re-indexing or backfilling metadata:

  ```powershell
  .\7didan-env\Scripts\python.exe scripts\export_db.py
  ```

- Restore manually:

  ```powershell
  psql -h localhost -U 7didan -d 7didan_db -f postgres\7didan_backup.sql
  ```

- `docker compose up` mounts this file into `/docker-entrypoint-initdb.d/`,
  so a **fresh** `postgres-data` volume is pre-loaded with the data
  automatically. Existing volumes are left untouched.
