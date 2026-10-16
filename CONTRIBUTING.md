# Contributing

Thank you for improving CipherScore. This repository combines ML, cryptography, backend security, database migrations, and two frontend surfaces; changes should preserve those boundaries.

## Workflow

1. Open an issue describing the change and its privacy/security impact.
2. Create a focused branch and avoid unrelated generated files.
3. Add or update tests and documentation.
4. Run backend tests, frontend tests/lint/build, and relevant OpenFHE verification.
5. Submit a pull request with measured evidence and migration/rollback notes where applicable.

## Rules

- Never commit `.env`, credentials, tokens, private keys, production logs, or customer data.
- Never replace real OpenFHE execution with a mock in production paths.
- Do not add raw financial fields or exact decrypted scores to administrative persistence.
- Fit preprocessing only on training data and regenerate both Python/C++ inputs after model changes.
- Use Alembic for schema changes; do not create production tables at application startup.
- Enforce authorization in FastAPI even when the frontend hides an action.
- Label simulated, planned, and measured results accurately; do not invent benchmark values.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
cd frontend
npm test
npm run lint
npm run build
```

Security-sensitive changes should include threat-model updates and tests for failure paths, privilege boundaries, redaction, and replay/lockout behavior.
