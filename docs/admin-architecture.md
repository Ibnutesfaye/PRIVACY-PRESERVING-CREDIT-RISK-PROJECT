# Advanced Admin Architecture

The admin system stores operational metadata only. `prediction_metadata` excludes financial features, raw vectors, exact scores, ciphertext contents, and cryptographic material. FastAPI remains a trusted preprocessing gateway. The OpenFHE program separates client/evaluator responsibilities in code but runs them in one process; production process/key isolation remains future work.

Implemented capabilities include secure authentication and RBAC, responsive protected navigation, measured overview data, privacy-safe prediction monitoring, FHE/privacy monitoring, governed model versions, administrator and permission management, audit/security triage, service-health polling, reports, notifications storage, and non-secret settings.

Migrations:

- `0001`: identities, roles, permissions, refresh tokens, audit and security events
- `0002`: privacy-safe prediction metadata
- `0003`: governed model versions
- `0004`: notifications, settings, and report records

Configure `.env`, run `alembic upgrade head`, then `python -m backend.scripts.seed_admin`. Optional demo data requires all four `DEMO_*_PASSWORD` variables before `python -m backend.scripts.seed_admin_demo`.

This is an academic prototype. Credit-risk predictions must not be the sole basis for lending decisions.
