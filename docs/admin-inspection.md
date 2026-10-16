# Existing Project Inspection and Admin Foundation Plan

## 1. Current folder structure

- `data/`: raw and processed dataset artifacts.
- `ml/`: inspection, preprocessing, logistic-regression training, model extraction, polynomial selection, and FHE input exporters.
- `openfhe/`: genuine OpenFHE C++ context, key generation, encrypted weighted sum, degree-7 polynomial inference, generated parameters, and local builds.
- `backend/`: small FastAPI gateway with schemas and an OpenFHE subprocess service.
- `frontend/`: React/Vite customer prediction interface.
- `benchmarks/`: normal/FHE benchmark aggregation and measured outputs.
- `tests/`: dataset, model, FHE, API, validation, and documentation tests.
- `docs/`: architecture, threat model, phase reports, research report, and demo material.

## 2. Frontend framework and version

React 19.2.8, React DOM 19.2.8, TypeScript 6.0.2, and Vite 8.2.0. The current application is a single responsive customer prediction page. It has no router, query cache, authentication state, or admin components.

## 3. Backend framework

FastAPI 0.115.12 with Pydantic and Uvicorn. The backend is a trusted local client gateway around the OpenFHE executable.

## 4. Database

No database or ORM existed before the admin work. Phase 1 introduces SQLAlchemy and Alembic with local SQLite. `ADMIN_DATABASE_URL` allows later PostgreSQL use without changing repositories or service interfaces.

## 5. Existing authentication

None. `/health` and `/predict` are public. There are no users, passwords, tokens, sessions, roles, or permissions.

## 6. Existing API routes

- `GET /health`
- `POST /predict`

## 7. Existing prediction workflow

The browser sends seven plaintext fields to trusted FastAPI. FastAPI validates them, applies the training-fitted imputer/scaler, writes a temporary scaled vector, and invokes the compiled C++ process. OpenFHE generates keys, encrypts the scaled features, evaluates the encrypted linear model and degree-7 polynomial, decrypts at the trusted boundary, and returns a score and timing. Temporary files are removed.

## 8. Existing OpenFHE integration

OpenFHE v1.5.1 is compiled with MSYS2 MinGW64. `day3_fhe_predict.cpp` implements genuine CKKS SIMD inference. The evaluator functions do not accept the secret key. FastAPI invokes `day3_fhe_predict.exe` as a subprocess.

## 9. Existing model artifacts

The artifacts directory contains the median imputer, StandardScaler, logistic-regression model, preprocessing metadata, and extracted model parameters. Seven numerical features are used in a fixed order.

## 10. Existing benchmark outputs

Measured JSON/CSV outputs contain normal/FHE metrics, phase timing, ciphertext sizes, polynomial errors, and complete decrypted FHE test probabilities. The final measured packed pipeline used 6,484 samples and ring dimension 32,768.

## 11. Existing admin-related code

None before this phase.

## 12. Existing files that require modification

- `requirements.txt`: database, migration, password-hashing, JWT, and email-validation dependencies.
- `.gitignore`: exclude database and secret environment files.
- `.env.example`: document required configuration without real credentials.
- `backend/app/main.py`: include versioned admin authentication routes and secure headers while preserving existing APIs.
- `README.md`: add admin foundation setup and migration commands.

## 13. New Phase 1 files

- Database configuration/session/base modules.
- Admin ORM models and role/permission constants.
- Security, token, password, audit, and authorization services.
- Authentication schemas and routes.
- Alembic configuration and initial migration.
- Safe environment-driven seed command.
- Authentication, RBAC, lockout, refresh, audit, and privacy tests.

Later phases will add dashboard aggregation, privacy-safe prediction metadata, FHE monitoring, model workflows, users/roles UI, reports, notifications, settings, and their migrations.

## 14. Current security risks

- Prediction endpoint has no authentication, quota, or durable rate limit.
- Local development uses HTTP rather than TLS.
- FastAPI is a trusted plaintext gateway and therefore a high-value endpoint.
- C++ evaluator errors can expose local technical detail through the current 500 response.
- No persistent audit trail, account control, token lifecycle, or security-event storage existed.
- Temporary plaintext-scaled files exist briefly on the gateway host.
- No production secret manager, key service, process isolation, or integrity verification is present.

## 15. Current privacy risks

- Browser inputs are plaintext at FastAPI; this is not browser-side FHE.
- The response includes a precise raw decrypted score, which can increase output-inference risk.
- Operational metadata can reveal timing and request patterns.
- The gateway host can inspect input and secret-key process memory.
- Future admin persistence could accidentally store raw features unless the schema and tests prohibit them.

## 16. Recommended implementation plan

1. Secure database/authentication foundation: migrations, Argon2id password hashes, short-lived JWT access tokens, opaque rotating refresh tokens, lockout, RBAC, and audit chain.
2. Responsive protected admin shell with React Router, theme, route/permission guards, and safe API client.
3. Overview aggregates sourced from measured data and clearly labeled demo records.
4. Privacy-safe prediction metadata persistence, pagination, filters, details, and timeline.
5. Privacy/FHE monitoring tied to real configuration and measured outputs; simulated controls explicitly labeled.
6. ML and model-version workflows with approvals, integrity hashes, confirmations, and audits.
7. Admin users, roles, and permission management enforced by backend dependencies.
8. Audit, security events, system health, reports, notifications, and validated settings.
9. Backend/frontend/privacy test suites and final responsive/security review.

