# Database

## Configuration and resilience

SQLAlchemy 2 and psycopg 3 use `pool_pre_ping=True`, a five-second PostgreSQL pool timeout, a five-second connect timeout, and explicit session lifecycles. Configuration accepts a URL environment value for local development or a Docker secret file. No production SQLite fallback exists; tests explicitly select isolated SQLite.

## Migration history

| Revision | Purpose |
|---|---|
| `20260805_0001` | administrators, RBAC, sessions, audit/security |
| `20260805_0002` | privacy-safe prediction metadata |
| `20260805_0003` | governed model versions |
| `20260805_0004` | notifications, settings, reports |
| `20260805_0005` | FHE/model metrics, benchmarks, health |
| `20260807_0006` | organizations, branches, memberships, consent, applications, workflow, decisions, profiles, retention |
| `20260807_0007` | nullable client-owned encryption/decryption metric stages |

Current verified head: `20260807_0007`. There are 28 application tables.

## Enterprise relations

An organization owns branches, consent records, applications, and retention policies. Memberships constrain a user to organization or branch scope. Applications reference consent, creator/assignee, a hashed customer reference, product code, model recommendation, coarse band, prediction ID, guarded status/version, and retention time. Workflow history and human decisions are append-oriented separate records. Prediction metadata can link application, organization, branch, and requesting user.

## Privacy

The schema cannot represent the seven raw financial features, exact decrypted FHE score, client secret key, or ciphertext body. The ciphertext endpoint stores only identifiers, status, model/profile, evaluator time, and request ciphertext size. Client-owned encryption/decryption times are `NULL`, never fabricated. Passwords are Argon2id hashes and refresh tokens are SHA-256 hashes.

## Operations

```powershell
python -m alembic current
python -m alembic upgrade head
python -m backend.scripts.sync_enterprise_rbac
python -m backend.scripts.backup_database D:\approved-backups\cipherscore.dump
python -m backend.scripts.verify_database_backup D:\approved-backups\cipherscore.dump
```

Run migrations once as an approved release action. Use least-privilege roles, private networking, TLS, encrypted backups/PITR, monitored connections, restore exercises, and legal-hold-aware retention. Do not rerun the interactive PostgreSQL credential setup on an already configured system.
