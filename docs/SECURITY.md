# Security and threat model

## Assets and trust boundaries

Restricted assets are customer financial features, client secret keys, administrator credentials/tokens, database/monitoring secrets, and consent/decision notes. Confidential assets include application metadata and encrypted payloads. Internal assets include model/profile identifiers, timings, and aggregate metrics. Public assets are approved documentation and non-sensitive health metadata.

The trusted client owns preprocessing, key generation, encryption, decryption, and presentation of the result. The FastAPI/evaluator tier is honest-but-curious for feature confidentiality and receives only seven ciphertexts, context, and evaluation keys. PostgreSQL is trusted for minimized workflow metadata but never receives raw model inputs or a decrypted score from the ciphertext endpoint.

## Implemented controls

- Argon2id passwords, short access JWTs, hashed/rotating refresh tokens, replay rejection, revocation, lockout, and per-process login throttling.
- Permission-based RBAC with organization/branch memberships and server-side scope checks.
- Guarded application transitions, optimistic version checks, separate human decisions, required override reasons, and hash-chained audit events.
- Validated configuration, HTTPS-only production origins, no wildcard CORS, request-size/ciphertext bounds, safe errors, CSP, HSTS, correlation IDs, and body-free structured logs.
- Split OpenFHE commands and serialized artifacts. The evaluator receives no secret-key path and rejects a request directory containing `secret-key.bin`.
- Authenticated ciphertext profile/evaluation APIs and protected Prometheus metrics using constant-time token comparison.
- Docker secrets, non-root API container, no-new-privileges, internal data/monitoring networks, TLS edge proxy, and no universal administrator seed.
- Privacy-safe persistence: hashes/references, state, profile/model IDs, timing, size, and audit metadata; no raw financial features.

## Threats and residual risk

| Threat | Current mitigation | Residual requirement |
|---|---|---|
| Curious evaluator | CKKS ciphertext-only process | Independent deployment and cryptographic review |
| Stolen client key | Key absent from server | Institution KMS/HSM, rotation, revocation, recovery |
| Credential attack | Argon2id, lockout, rotation | Shared rate limiter, MFA/SSO, anomaly detection |
| Cross-branch access | Membership scope checks | Comprehensive authorization tests and policy review |
| Payload/availability abuse | Bounds, timeouts, proxy limits | Quotas, queue admission, memory/circuit breakers |
| Dependency/build compromise | Pins, CI, npm audit, hashes | SBOM, signing, provenance, continuous scanning |
| Metadata/traffic analysis | Data minimization | Network controls, padding/batching study where necessary |
| Database/operator compromise | Minimized fields, audit | Managed encryption, privileged-access controls, monitored backups |
| Malicious/compromised client | Server validation | Device trust, signed client, attestation where justified |
| Incorrect credit decision | Human workflow and override records | Legal/model/fairness validation and officer policy |

FHE protects feature confidentiality during supported computation. It does not prove result integrity, protect model parameters, authenticate users, secure transport, or make the surrounding application safe by itself.

## Secret handling

Never log, commit, paste, or return passwords, URLs containing credentials, JWT/refresh tokens, monitoring tokens, private keys, raw inputs, or production backup contents. Configuration supports Docker secret files. Rotate any secret exposed through a traceback, terminal capture, screenshot, issue, commit, or CI artifact.

## Incident and production gates

Before pilot approval: establish a private reporting channel; assign owners/severity/SLA; centralize auth/rate-limit/security telemetry; rehearse token/key compromise, database restore, evaluator failure, and rollback; perform dependency/container scans, penetration testing, and an OpenFHE parameter/protocol review. A failed readiness, migration, backup verification, authorization test, or ciphertext-equivalence test blocks release.
