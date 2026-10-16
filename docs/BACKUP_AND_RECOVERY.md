# Backup and recovery runbook

Use a dedicated, access-controlled backup location with encryption at rest. Create a custom-format PostgreSQL backup without exposing credentials in process arguments:

```powershell
python -m backend.scripts.backup_database D:\approved-backups\cipherscore-2026-08-07.dump
python -m backend.scripts.verify_database_backup D:\approved-backups\cipherscore-2026-08-07.dump
```

The backup tool obtains the configured SQLAlchemy URL, passes the password only in the child process environment, suppresses native output on failure, removes incomplete files, and creates a SHA-256 sidecar. Never place backup files inside the repository.

Recovery must be rehearsed into a separate empty database using `pg_restore --exit-on-error --no-owner --no-privileges`, followed by `alembic current`, the PostgreSQL verification script, API readiness, authentication, application/workflow, and metadata/FHE linkage tests. In-place restore is deliberately not automated because it can overwrite live data. Require change approval, a maintenance window, verified rollback media, and a second operator before restoring production.

For the controlled rehearsal, a DBA first creates an empty database without granting `CREATEDB` to the application role. The operator then sets the target URL only in the local process and runs:

```powershell
$env:CIPHERSCORE_RESTORE_DATABASE_URL = Read-Host "Clean rehearsal database URL" -MaskInput
python -m backend.scripts.restore_rehearsal C:\tmp\cipherscore-restore-rehearsal-20260807.dump
Remove-Item Env:CIPHERSCORE_RESTORE_DATABASE_URL
```

The script verifies SHA-256, refuses the working database, restores without owners/privileges, advances/verifies migrations, and reports only revision/table/representative record counts. It never creates or drops a database. The DBA should drop the rehearsal database after evidence approval according to institutional procedure.

Back up the approved public OpenFHE profile and its hashes separately. Do not place client secret keys in server backups. Client-key recovery is an institution-owned KMS/HSM process. Define and test recovery-point and recovery-time objectives before pilot approval.
