# Final pilot blocker-closure report

Date: 2026-08-07  
Scope: executable verification on the Windows development workstation. PASS means this run produced executable evidence; configuration alone is not PASS.

## Decision

The full trusted-client-to-authenticated-API encrypted workflow now passes over real loopback HTTP, and workstation OpenFHE capacity, backup, application, and security regression evidence is current. The deployment is **not yet technically ready for a controlled institutional pilot** because Docker/TLS/Redis/Prometheus live validation, k6 load execution, and a DBA-controlled restore rehearsal remain blocked on this workstation. Operational HSM/KMS approval also remains external.

## Acceptance matrix

| # | Area | Status | Executable evidence or blocker |
|---:|---|---|---|
| 1 | End-to-end OpenFHE computation | PASS | Isolated Uvicorn acceptance completed login → local preprocess/encrypt → authenticated ciphertext API → native evaluation → encrypted response → local decrypt. |
| 2 | Local preprocessing | PASS | Training-fitted imputer/scaler and exact feature-order regression tests pass. |
| 3 | Local encryption | PASS | Acceptance client invoked real OpenFHE encryption before HTTP. |
| 4 | Server secret-key isolation | PASS | Server profile contained only context, public/evaluation keys, and profile; `secret_key_in_server_profile=false`. |
| 5 | Ciphertext-only API | PASS | Request schema accepts seven ciphertexts plus non-sensitive protocol metadata; raw sentinels absent from logs/database. |
| 6 | Encrypted result | PASS | API returned serialized ciphertext and no risk score. |
| 7 | Local decryption | PASS | Trusted client alone decrypted `0.27980674535678396`. |
| 8 | Plaintext/FHE agreement | PASS | Live acceptance error `6.499967231121673e-12`, same class. Separate fresh 247-sample run had 100% agreement and zero crossings. |
| 9 | Authentication | PASS | Real temporary authorized user login succeeded; expired/invalid/replay/lockout tests pass. |
| 10 | RBAC | PASS | Real acceptance caller had `applications.write`; denial/role tests pass. |
| 11 | Workflow | PASS | Guarded workflow and separate human decision/override records pass automated tests. |
| 12 | PostgreSQL | PASS | Live development DB remains migration `20260807_0007`, 28 tables; no credentials changed. |
| 13 | Audit logging | PASS | Auth/evaluation audit tests and linked acceptance metadata/FHE metric pass. |
| 14 | Privacy-safe logging | PASS | Acceptance sentinels absent from server output and isolated DB; repository log/persistence rescan found no sensitive-value logging call. |
| 15 | Docker runtime | BLOCKED | `docker` and Compose unavailable locally. Static YAML parses; Dockerfile issue fixed; CI now defines live Compose build/start/health checks. Not executed here. |
| 16 | Nginx/TLS | BLOCKED | OpenSSL is available and configuration is hardened, but Nginx/Docker is unavailable; no live handshake, routing, redirect, or header evidence. |
| 17 | Redis | BLOCKED | Redis CLI/runtime unavailable. Authenticated internal Compose/CI check exists; application currently has no distributed FHE queue, so queue behavior is not claimed. |
| 18 | Prometheus | PARTIAL | Metrics endpoint tests cover auth plus API/FHE/auth-failure/database/readiness/worker metric names and sensitive-label exclusions. No live scrape/target evidence. |
| 19 | Backup | PASS | Fresh `106,719`-byte custom dump and SHA-256 sidecar created under `C:\tmp`; checksum verified. |
| 20 | Restore | BLOCKED | Verified dump exists, but application role correctly has `CREATEDB=false`; DBA must create clean DB. Safe restore script refuses working DB and never creates/drops databases. |
| 21 | Load testing | BLOCKED | k6 unavailable. Harness syntax passes and CI runs liveness load; full authorized encrypted mixed-load results do not exist. |
| 22 | Capacity benchmark | PASS | Five runs each for SIMD batches 1/64/247 with mean/median/p95/p99/min/max/stddev, sizes, hardware, OS and OpenFHE profile recorded. Workstation-only evidence. |
| 23 | Key custody | PARTIAL | Local keystore boundary and dual-control lifecycle ceremony are documented; no real HSM/KMS, signed client, or institutional ceremony executed. |
| 24 | Malformed-input safety | PASS | Corrupt, truncated, empty, random, incompatible, wrong-key and count failures are safe; API context/profile/model fingerprint regressions pass. Parameter-identical context compatibility is documented as expected OpenFHE behavior. |
| 25 | Failure recovery | PARTIAL | DB unavailable, evaluator unavailable/timeout, malformed input, expired token, revoked refresh, wrong role/model/profile tests return safe correlated errors. Redis/container recovery cannot be executed locally. |
| 26 | Documentation | PASS | Protocol/context analysis, key ceremony, restore handoff, CI gates, load harness, deployment runbook and this report are current. |

## Environment detection

| Tool | Result |
|---|---|
| Docker / Compose | unavailable |
| k6 | unavailable |
| redis-cli | unavailable |
| PostgreSQL psql | 18.2 at `C:\Program Files\PostgreSQL\18\bin\psql.exe` |
| pg_dump | 18.2 at `C:\Program Files\PostgreSQL\18\bin\pg_dump.exe` |
| OpenSSL | 3.2.4 (Git distribution) |
| curl | 8.21.0 (Windows/Schannel) |

## Full encrypted acceptance result

Machine-readable evidence: `benchmarks/results/live_encrypted_acceptance.json`.

- Real isolated Uvicorn HTTP service: PASS.
- Authentication/authorization: PASS.
- Metadata row and linked FHE metric: PASS.
- Plain circuit: `0.2798067453632839`.
- Decrypted FHE: `0.27980674535678396`.
- Absolute error: `6.499967231121673e-12`; classification agreement: true.
- Server-side secret key: false.
- Raw sentinels in server logs/database: false.
- Secret/token material in server logs: false.
- Remaining evaluator temporary entries: 0.

The acceptance database, user, password, JWT secret, client private directory, and server acceptance profile were temporary and removed after the run. The working PostgreSQL database and credentials were not modified.

## OpenFHE capacity results

Hardware: Intel64 Family 6 Model 142, 8 logical CPUs, 16,976,740,352 bytes RAM, Windows 11 build 26200. OpenFHE 1.5.1, CKKS, ring 32,768, depth 6, 50-bit scaling modulus, 60-bit first modulus, `FLEXIBLEAUTOEXT`, `HYBRID`, `HEStd_128_classic`. Each configuration used five new-key runs.

| Batch | Total mean | Median | p95 | p99 | Min | Max | SD |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2023.515 ms | 2031.847 | 2158.828 | 2165.562 | 1839.416 | 2167.245 | 118.150 |
| 64 | 1867.365 ms | 1871.829 | 1872.990 | 1873.174 | 1859.402 | 1873.220 | 6.159 |
| 247 | 1911.245 ms | 1910.910 | 1978.569 | 1989.327 | 1856.045 | 1992.017 | 47.451 |

For batch 247, stage means were key generation `323.587 ms`, encryption/serialization `552.501 ms`, encrypted evaluation/serialization `852.679 ms`, and decryption/deserialization `182.477 ms`. All batches serialized to a `29,374,863`-byte request and `1,050,085`-byte response because CKKS packing capacity is fixed. These measurements are not an SLA or production sizing guarantee. Full distributions are in `benchmarks/results/fhe_capacity.json`.

## Exact commands and results

```powershell
# Environment versions
docker --version                         # unavailable
k6 version                              # unavailable
C:\Program Files\PostgreSQL\18\bin\psql.exe --version     # 18.2
C:\Program Files\PostgreSQL\18\bin\pg_dump.exe --version  # 18.2
C:\Program Files\Git\usr\bin\openssl.exe version           # 3.2.4
C:\Windows\System32\curl.exe --version                      # 8.21.0

python -m scripts.live_encrypted_acceptance
# PASS; exact values listed above

python -m benchmarks.fhe_capacity --runs 5 --batches 1,64,247
# PASS; 15 total measured OpenFHE runs

python -m backend.scripts.backup_database C:\tmp\cipherscore-restore-rehearsal-20260807.dump
python -m backend.scripts.verify_database_backup C:\tmp\cipherscore-restore-rehearsal-20260807.dump
# PASS; dump 106,719 bytes and SHA-256 verified

python -m pytest -q -p no:cacheprovider
# 58 passed in 9.30s

npm run lint
# PASS
npm test -- --run
# 1 file, 3 tests passed in 3.26s
npm run build
# PASS; 2,381 modules transformed

node --check tests/load/k6-smoke.js
node --check tests/load/k6-pilot.js
# PASS

python -c "import yaml; ..."
# PASS: compose.yaml, CI workflow and Prometheus YAML parsed
```

The project `.venv` launcher still references a removed Python installation; commands used bundled Python 3.12.13 with the existing project site-packages. No credential, database URL, JWT secret, token, private key, or secret-key bytes were printed.

## Restore handoff

The DBA creates a separate empty rehearsal database and grants only the permissions required to restore/test. The operator supplies its URL locally through masked input and runs `python -m backend.scripts.restore_rehearsal <verified.dump>`. The script validates SHA-256, refuses the working database, uses `pg_restore --exit-on-error --no-owner --no-privileges`, upgrades/verifies Alembic, and reports table and representative row counts. Live restore remains BLOCKED until that DBA action occurs.

## Security findings and residual risk

- Context fingerprint, profile and model version are now validated before native evaluation. SHA-256 prevents accidental context mixing; it does not prove ciphertext provenance.
- OpenFHE parameter-identical contexts are structurally compatible by design. Key tags/material enforce the cryptographic identity; wrong evaluation/public keys failed safely.
- Authentication failures and DB/application/worker readiness now have privacy-safe Prometheus metrics. There is no queue, therefore no queue-depth metric is claimed.
- CI now includes live Compose generation/start checks and a real k6 liveness job on suitable hosted runners. Those definitions are not evidence that the jobs have run.
- Remaining external work: live Docker/TLS/Redis/Prometheus acceptance, full encrypted k6 capacity testing, DBA restore rehearsal, shared rate limiting/queue design if required, independent penetration/cryptographic review, and institution-approved HSM/KMS ceremony.

## Files changed in this blocker-closure pass

- `.github/workflows/ci.yml`
- `backend/app/encrypted_routes.py`, `backend/app/encrypted_schemas.py`, `backend/app/encrypted_service.py`, `backend/app/main.py`, `backend/app/observability.py`
- `backend/scripts/backup_database.py`, `backend/scripts/restore_rehearsal.py`, `backend/scripts/validate_encrypted_api.py`
- `trusted_client/client.py`
- `scripts/live_encrypted_acceptance.py`
- `benchmarks/fhe_capacity.py`
- `benchmarks/results/live_encrypted_acceptance.json`, `benchmarks/results/fhe_capacity.json`
- `tests/test_encrypted_contract.py`, `tests/test_enterprise_foundation.py`
- `docs/BACKUP_AND_RECOVERY.md`, `docs/ENCRYPTED_PROTOCOL.md`, `docs/TRUSTED_CLIENT_AND_KEY_MANAGEMENT.md`, `docs/PILOT_READINESS_REPORT.md`

## Final conclusion

The target statement **“Technically ready for a controlled institutional pilot” is not yet supported**. Cryptographic, application, real encrypted HTTP acceptance, capacity benchmarking, and backup gates pass. Live infrastructure/load/restore and approved operational key custody remain blockers.

Production lending additionally requires institution-specific historical model validation, fairness validation, organizational security approval, legal/regulatory review, approved operational key custody, production infrastructure sizing, and institutional change-management approval.
