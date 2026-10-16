# Changelog

All notable changes to this research prototype are documented here. The format follows Keep a Changelog principles; the project does not yet publish semantic-version tags.

## Unreleased

### Added

- PostgreSQL 18 persistence through revision `20260807_0007` and idempotent secure setup.
- JWT/Argon2 administrator authentication, rotating refresh tokens, RBAC, lockout, audit, and security events.
- Privacy-safe prediction/FHE metrics, model governance, reports, notifications, settings, and system-health views.
- Customer-to-admin navigation with protected-route enforcement.
- Production/research documentation set and endpoint catalog.
- Split-process OpenFHE setup/encrypt/evaluate/decrypt protocol and authenticated ciphertext-only API.
- Organizations, branches, memberships, consent, applications, workflow history, human decisions, crypto profiles, and retention policies.
- Protected Prometheus metrics, deployment/CI/load assets, and backup verification tooling.

### Changed

- Hardened native setup execution to use exit codes rather than stderr presence and redact secrets.
- Added PostgreSQL pool pre-ping and bounded pool/connect timeouts.
- Corrected PostgreSQL date aggregation and `.env` loading for administrator security settings.
- Made administrator seeding and database setup safe to repeat.
- Replaced the single-process privacy boundary with serialized client/evaluator artifacts and client-only decryption.
- Versioned the threshold and added a SHA-256 model governance manifest.

### Security

- Excluded raw financial fields from administrative persistence.
- Added security headers, generic authentication failures, permission dependencies, and hashed refresh-token storage.
- Confirmed `.env`, credentials, local databases, builds, dependencies, and caches are ignored.
- Enforced encrypted-endpoint authentication, branch scope, guarded transitions, and model-override reasons.

### Verified

- Real OpenFHE CKKS prediction and saved approximation/latency evidence.
- Backend and frontend automated tests, TypeScript build, PostgreSQL migration/persistence, login, dashboard, and restart persistence.
- 6,484-sample ciphertext transport/decrypt equivalence, three-run split benchmark, 45 backend tests, frontend lint/tests/build, and npm production audit.
