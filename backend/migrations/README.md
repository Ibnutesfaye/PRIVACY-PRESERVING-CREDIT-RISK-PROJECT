# Admin database migrations

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

`ADMIN_DATABASE_URL` overrides the local SQLite URL. Production PostgreSQL requires an appropriate driver and reviewed deployment configuration.

