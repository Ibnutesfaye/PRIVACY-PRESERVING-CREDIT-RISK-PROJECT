# Deployment Guide

## Readiness statement

The repository includes a controlled pilot Compose profile and a Linux-native OpenFHE build, while local development remains Windows-based. Live container acceptance was not run on this workstation because Docker is unavailable. It is not approved for autonomous or production lending decisions.

## Release pipeline

1. Run secret/dependency/static analysis and all tests.
2. Reproduce ML/FHE artifacts from immutable inputs when they change.
3. Build the native evaluator in Release mode for the target platform.
4. Build the frontend with an explicit API origin.
5. Build an immutable backend image/package containing only required runtime artifacts.
6. Back up PostgreSQL and run `alembic upgrade head` as a controlled release job.
7. Deploy backend, then frontend; verify health, auth, prediction, persistence, and rollback.

## Runtime configuration

Inject, never bake: database URL, JWT signing secret, allowed origins, monitoring credentials, and any external key-management configuration. Restrict environment and secret-file permissions to the service identity.

## Backend

Run Uvicorn behind a production reverse proxy/process manager. Configure bounded workers based on native FHE CPU/memory measurements; unbounded parallel predictions can exhaust the host. Use request-size/time limits and graceful shutdown. Avoid request-body logging.

## Frontend

Serve `frontend/dist` as immutable static assets with SPA fallback to `index.html`. Set `VITE_API_URL` at build time, enable CSP, HSTS, compression, and long-lived hashed-asset caching while keeping `index.html` short-lived.

## Database

Use managed PostgreSQL or a hardened dedicated service with TLS, private networking, least privileges, automated backups/PITR, connection monitoring, and tested restore procedures. Do not run setup prompts inside application containers.

## OpenFHE

Pin the OpenFHE version and compiler, verify the evaluator during image build, ship required shared libraries, run as an unprivileged user, and isolate writable temporary storage. The protocol separates client key ownership from the evaluator process; a pilot must also deploy them in separate security domains and keep `secret-key.bin` out of server profiles, images, and backups.

## Observability

Collect request IDs, status codes, aggregate latency, native process failures, pool saturation, authentication/security events, and host resource use. Exclude bodies, tokens, URLs containing credentials, raw features, ciphertext/key material, and exact decrypted scores.

## Rollback

Retain the previous application/native artifacts. Prefer backward-compatible expand/migrate/contract database releases. Application rollback does not automatically reverse migrations; test downgrade/recovery procedures separately.

## Production checklist

- [ ] TLS/HSTS and restricted CORS
- [ ] Vault/KMS secret delivery and rotation
- [ ] SSO/MFA and shared rate limiter
- [ ] Managed backups and restore test
- [ ] Resource/concurrency limits based on FHE memory profiling
- [ ] Central privacy-safe logs, metrics, alerts
- [ ] Dependency/SBOM/container scanning
- [ ] Fairness, calibration, legal, and model-risk approval
- [ ] Browser/client encryption or separately isolated key owner
- [ ] CI Linux OpenFHE container build and signed image provenance
- [ ] Incident response and rollback rehearsed
