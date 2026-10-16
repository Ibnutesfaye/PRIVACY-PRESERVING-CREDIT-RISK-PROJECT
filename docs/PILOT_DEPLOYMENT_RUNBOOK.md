# Controlled institutional pilot runbook

This runbook requires named infrastructure, database, security, model-risk, and operations owners. It does not authorize autonomous credit decisions.

1. **Infrastructure:** provision isolated Docker-capable pilot hosts, private DNS, NTP, encrypted disks, outbound restrictions, capacity monitoring, and approved image registry. Validate `docker compose config`, build, scan, and sign images.
2. **PostgreSQL:** create a least-privilege application role and database through the approved DBA process. Keep DDL/bootstrap credentials out of runtime. Apply Alembic and record `alembic current` and schema checks.
3. **Redis:** provision authenticated Redis on the internal data network with persistence, memory limits, backups where required, and no public port. The present application does not yet use a distributed FHE queue.
4. **TLS:** issue a certificate for the pilot hostname, provision `deployment/certs` outside version control, allow TLS 1.2/1.3, validate chain/hostname/expiry and secure headers, and redirect or close plaintext ports.
5. **Environment:** provision Docker secret files for database URL, JWT key, metrics token, PostgreSQL password, and Redis ACL. Set only approved HTTPS CORS origins and keep plaintext prediction disabled.
6. **Admin bootstrap:** use the secure masked, idempotent bootstrap procedure once. Assign organization/branch memberships and least permissions; test lockout, refresh rotation, and revocation.
7. **Trusted client:** install the signed package on an institution-managed encrypted device. Validate Python/native dependencies and endpoint/TLS trust. The browser must not custody the FHE secret key.
8. **FHE keys:** run `python -m trusted_client init-keys --public-bundle <approved-export> --key-dir <private-store>` on the trusted device. Apply restrictive ACLs; escrow only through the approved vault/HSM ceremony.
9. **Evaluation keys:** transfer only context, public key, evaluation multiplication keys, and profile JSON to the evaluator profile mount. Verify hashes and confirm `secret-key.bin` is absent.
10. **Model:** deploy the independently approved model/profile pair; verify model manifest hashes, feature order, preprocessing coefficients, polynomial, parameter profile, and institution validation sign-off.
11. **Smoke tests:** check liveness/readiness, admin authentication, RBAC denial, one fresh encrypted request, local decryption, linked metadata/FHE metric rows, audit event, and restart persistence. Never use real customer data for smoke tests.
12. **Monitoring:** protect Prometheus; alert on readiness/database/evaluator failures, auth failures, HTTP/FHE latency/error rates, disk/certificate expiry, and resource saturation. Do not label metrics with customer values.
13. **Backup:** run an encrypted PostgreSQL backup and SHA-256 verification on schedule. Back up approved public profiles separately. Secret-key escrow is a client custody process.
14. **Rollback:** stop intake, preserve audit evidence, revert the application/model/profile to the last signed compatible release, run migrations only under the tested rollback policy, smoke test, then reopen with approval.
15. **Incident:** isolate the affected tier; revoke sessions/profile access; preserve logs; notify security/privacy/model-risk owners; rotate exposed secrets/keys; assess customer and regulatory impact; recover from verified media; document root cause and approval to resume.

Before go-live, execute the restore rehearsal and 1/10/25/50/100-user authorized load plan on target-like infrastructure. A failed restore, ciphertext-equivalence, authorization, key-custody, TLS, container, or capacity check blocks deployment.

