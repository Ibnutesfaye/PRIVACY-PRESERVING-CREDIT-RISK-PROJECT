# Financial-institution pilot deployment

This profile targets a controlled 20–100-user, 1–10-branch pilot. It is not an automatic production deployment.

The Linux backend image compiles pinned OpenFHE `v1.5.1` and the native evaluator inside the container build. It does not copy or attempt to run the Windows `.exe`. PostgreSQL and Redis are isolated from the public network. Nginx terminates TLS and exposes only the UI and versioned API. Prometheus reaches the protected internal metrics endpoint on a separate internal network.

Before a controlled deployment, an operator must provision the Docker secret files referenced by `compose.yaml` under `deployment/secrets`, TLS certificate/key files under `deployment/certs`, and a public OpenFHE profile under `deployment/openfhe-public-profile`. The database URL secret must be a correctly URL-encoded SQLAlchemy URL. The Redis ACL secret is a Redis ACL file rather than a plaintext command-line argument. The OpenFHE server profile may contain `context.bin`, `public-key.bin`, `evaluation-mult-keys.bin`, and `profile.json`; it must never contain `secret-key.bin`.

Run configuration validation before building:

```powershell
docker compose config --quiet
docker compose build backend frontend
docker compose up -d
docker compose ps
```

The backend entrypoint applies Alembic migrations and idempotently synchronizes RBAC. It never creates a universal administrator. Use the existing explicit secure administrator bootstrap process after the services are healthy.

Backups must cover PostgreSQL and the approved non-secret OpenFHE public profile. Private client keys require a separate institution-approved key-management and recovery process and must not be included in server backups.
