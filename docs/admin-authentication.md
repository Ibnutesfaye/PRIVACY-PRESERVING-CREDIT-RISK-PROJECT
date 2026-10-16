# Admin Phase 1: Database and Authentication

This phase adds the security foundation only. It deliberately does not add dashboard pages, customer records, prediction-history persistence, monitoring, or model-management mutations.

## Design

- SQLAlchemy 2 models and Alembic migrations are the database source of truth.
- SQLite is the local default; `ADMIN_DATABASE_URL` can point to PostgreSQL in deployment.
- Passwords use Argon2id and must be at least 14 characters with upper/lowercase, a number, and a symbol.
- Access tokens are short-lived signed JWTs. Refresh tokens are opaque random secrets; only SHA-256 hashes are stored.
- Refresh tokens rotate on every use and are revocable at logout.
- Authorization is loaded from the database on every protected request, so role changes take effect without waiting for access-token expiry.
- Repeated failures cause a durable account lockout and a security event. A per-process IP limiter provides additional local protection; production must use a shared limiter such as Redis at the reverse proxy/application layer.
- Audit records form a SHA-256 hash chain. They are tamper-evident, not magically immutable; production should also export them to append-only storage or a SIEM.

## Roles

The migration-ready seed service creates `super_admin`, `ml_fhe_analyst`, `auditor`, and `support_admin`, plus explicit permission codes. Routes should require permission dependencies rather than checking role names.

## Setup

Copy `.env.example` to `.env` and replace every placeholder. Never commit the resulting file.

```powershell
alembic upgrade head
python -m backend.scripts.seed_admin
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Authentication endpoints:

- `POST /api/admin/auth/login`
- `POST /api/admin/auth/refresh`
- `POST /api/admin/auth/logout`
- `GET /api/admin/auth/me`

API errors have a stable envelope containing `success`, `error.code`, `error.message`, and `error.request_id`. Authentication responses are marked `Cache-Control: no-store`. Raw passwords, token values, customer financial inputs, and OpenFHE secret-key material are prohibited from audit metadata.

## Deployment controls still required

Use TLS, a trusted secret manager, a strong randomly generated JWT secret, PostgreSQL backups, database least privilege, reverse-proxy rate limits, centralized monitoring, secure refresh-token handling, and restricted access to audit exports. The current browser prototype should not store refresh tokens in local storage; a later UI phase should use a secure, HttpOnly, SameSite cookie/BFF design.
