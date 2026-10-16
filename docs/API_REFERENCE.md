# API Reference

Base URL: `http://127.0.0.1:8000`. JSON is used unless CSV export is noted. Interactive schemas and generated request/response models are available at `/docs` and `/redoc`.

## Common responses

- `401`: missing, expired, invalid, or replayed credentials.
- `403`: authenticated account lacks a required permission.
- `404`: requested governed resource does not exist.
- `422`: request validation failed.
- `429`: login rate limit reached.
- `500`: encrypted evaluation or internal operation failed.
- `503`: administrator security configuration is unavailable.

Admin errors use `{"success":false,"error":{"code":"...","message":"...","request_id":"..."}}`. Protected endpoints require `Authorization: Bearer <access-token>`.

## System and compatibility endpoints

### `GET /health`

Summary: report API dependencies without secrets. Response example: `{"status":"healthy","database":"postgresql","connected":true,"openfhe":"ready"}`. Status: `200` (the body reports degraded dependencies).

### `POST /predict`

Summary: run validated CKKS credit-risk inference and persist privacy-safe metadata.

Request example:

```json
{"person_age":28,"person_income":45000,"person_emp_length":5,"loan_amnt":10000,"loan_int_rate":11.5,"loan_percent_income":0.22,"cb_person_cred_hist_length":6}
```

Response example (timings vary):

```json
{"risk_score":0.2684,"raw_fhe_score":0.2684,"prediction":"LOW RISK","timing":{"key_generation_ms":350,"encryption_ms":613,"evaluation_ms":947,"decryption_ms":102,"total_latency_ms":2344},"privacy":{"scheme":"OpenFHE CKKS","encrypted_inference":true,"evaluator_received_plaintext_features":false,"trusted_gateway_received_plaintext_features":true,"secret_key_available_to_evaluator":false,"architecture_note":"Academic local prototype"}}
```

Status: `200`, `422`, `500`.

`POST /predict` is a trusted-gateway research compatibility endpoint. Production validation requires `MODEL_PLAINTEXT_PREDICTION_ENABLED=false`.

### Ciphertext-only API (`applications.write`)

| Method and path | Description |
|---|---|
| `GET /api/v1/fhe/profiles/current` | Active non-secret profile metadata and readiness |
| `GET /api/v1/fhe/profiles/current/artifacts/context` | Serialized CKKS context |
| `GET /api/v1/fhe/profiles/current/artifacts/public-key` | Serialized public key; evaluation/secret keys are not exposed |
| `POST /api/v1/fhe/evaluate` | Accept exactly seven Base64 ciphertexts and return one result ciphertext |

The evaluation response includes `prediction_id`, `evaluation_time_ms`, and `evaluator_decrypted_result:false`; it never includes a plaintext risk score. Request bodies are bounded to 50 MB and decoded ciphertext bundles to 40 MB by default.

### Enterprise workflow

| Method and path | Permission | Purpose |
|---|---|---|
| `POST/GET /api/v1/organizations` | `organizations.write/read` | Create/list institutions |
| `POST/GET /api/v1/organizations/{id}/branches` | `organizations.write/read` | Create/list scoped branches |
| `POST /api/v1/organizations/{id}/memberships` | `organizations.write` | Assign organization/branch scope |
| `POST /api/v1/organizations/{id}/consents` | `applications.write` | Record minimized consent metadata |
| `POST/GET /api/v1/applications` | `applications.write/read` | Create/list minimized applications |
| `GET /api/v1/applications/{id}` | `applications.read` | Retrieve an authorized application |
| `GET /api/v1/applications/{id}/history` | `applications.read` | Retrieve workflow history |
| `POST /api/v1/applications/{id}/transitions` | `applications.review` | Apply an authorized state transition |
| `POST /api/v1/applications/{id}/prediction-reference` | `applications.write` | Link an encrypted prediction recommendation |
| `POST /api/v1/applications/{id}/decision` | `applications.approve` | Record a separate human decision and override reason |

`GET /api/v1/system/liveness` is process-only. `GET /api/v1/system/readiness` reports non-secret database/evaluator/profile checks. `/internal/metrics` is outside OpenAPI and requires the configured monitoring bearer token.

## Authentication

| Method and path | Summary | Request example | Success | Status codes |
|---|---|---|---|---|
| `POST /api/admin/auth/login` | Verify administrator and issue tokens | `{"email":"admin@example.com","password":"<secret>"}` | token response + identity | 200, 401, 403, 423, 429, 503 |
| `POST /api/admin/auth/refresh` | Rotate a refresh token | `{"refresh_token":"<opaque>"}` | replacement token response | 200, 401, 503 |
| `POST /api/admin/auth/logout` | Revoke current refresh token | `{"refresh_token":"<opaque>"}` | `{"success":true,"message":"Logged out"}` | 200, 401 |
| `GET /api/admin/auth/me` | Return current identity and authorization | none | identity, roles, permissions | 200, 401 |

## Dashboard and predictions

| Method and path | Permission | Description | Response example/shape | Status |
|---|---|---|---|---|
| `GET /api/admin/dashboard/summary` | `dashboard.read` | operational counters + saved research metrics | `{operational_predictions, measured_research, system}` | 200, 401, 403 |
| `GET /api/admin/dashboard/activity?days=7` | `dashboard.read` | daily audit/prediction activity | `{series, recent}` | 200, 401, 403, 422 |
| `GET /api/admin/dashboard/risk-distribution` | `dashboard.read` | grouped risk classes | `{source,total,items}` | 200, 401, 403 |
| `GET /api/admin/dashboard/fhe-performance` | `dashboard.read` | measured saved FHE timings | `{scheme,stages,total_latency_ms}` | 200, 401, 403 |
| `GET /api/admin/dashboard/privacy` | `dashboard.read` | implemented/planned privacy controls | `{checks,boundary,note}` | 200, 401, 403 |
| `GET /api/admin/predictions` | `predictions.read` | paginated/filterable metadata | `{items,page,page_size,total}` | 200, 401, 403, 422 |
| `GET /api/admin/predictions/export` | `predictions.export` | privacy-safe CSV export | CSV attachment | 200, 401, 403 |
| `GET /api/admin/predictions/{id}` | `predictions.read` | one metadata record | prediction metadata object | 200, 401, 403, 404 |
| `GET /api/admin/predictions/{id}/timeline` | `predictions.read` | derived processing timeline | `{items:[...]}` | 200, 401, 403, 404 |

List example: `GET /api/admin/predictions?page=1&page_size=15&risk_class=HIGH%20RISK&sort_by=created_at&sort_order=desc`.

## FHE and model governance

| Method and path | Permission | Description | Request / response | Status |
|---|---|---|---|---|
| `GET /api/admin/fhe/metrics` | `fhe.read` | saved research configuration and stage metrics | `{scheme,ring_dimension,stages,...}` | 200, 401, 403 |
| `GET /api/admin/fhe/operational-metrics` | `fhe.read` | persisted per-prediction FHE metrics | `{items,total}` | 200, 401, 403 |
| `GET /api/admin/fhe/profiles` | `fhe.read` | approved CKKS profiles | `{items}` | 200, 401, 403 |
| `POST /api/admin/fhe/benchmarks` | `fhe.benchmark` | record an approved measured benchmark | no body; `{run_id,result}` | 200, 401, 403 |
| `GET /api/admin/models` | `model.read` | governed model versions | `{items}` | 200, 401, 403 |
| `GET /api/admin/models/metrics` | `model.read` | active model metrics/coefficients | `{model,parameters,causality_note}` | 200, 401, 403 |
| `POST /api/admin/models/{id}/approve` | `model.approve` | approve a validated model | no body; model object | 200, 400, 401, 403, 404 |
| `POST /api/admin/models/{id}/activate` | `model.activate` | activate approved FHE-compatible model | no body; model object | 200, 400, 401, 403, 404 |
| `POST /api/admin/models/{id}/archive` | `model.activate` | archive inactive model | no body; model object | 200, 400, 401, 403, 404 |

## Administration and operations

| Method and path | Permission | Description | Request example / response | Status |
|---|---|---|---|---|
| `GET /api/admin/users` | `users.read` | list administrators | `{items}` | 200, 401, 403 |
| `POST /api/admin/users` | `users.write` | create administrator | `{"email":"a@example.com","full_name":"A","password":"<strong>","role_ids":["..."]}` | 201, 400, 401, 403, 422 |
| `PATCH /api/admin/users/{id}` | `users.write` | update safe account fields | partial user object | 200, 401, 403, 404, 422 |
| `POST /api/admin/users/{id}/suspend` | `users.write` | suspend account | no body | 200, 400, 401, 403, 404 |
| `POST /api/admin/users/{id}/revoke-sessions` | `users.write` | revoke active sessions | no body | 200, 401, 403, 404 |
| `GET /api/admin/roles` | `roles.read` | roles, permissions, matrix | `{items,permissions}` | 200, 401, 403 |
| `POST /api/admin/roles` | `roles.write` | create role | `{"name":"analyst","description":"...","permission_codes":["dashboard.read"]}` | 201, 400, 401, 403, 422 |
| `PATCH /api/admin/roles/{id}` | `roles.write` | update role permission set | partial role object | 200, 400, 401, 403, 404 |
| `GET /api/admin/audit-logs` | `audit.read` | paginated tamper-evident events | `{items,total}` | 200, 401, 403, 422 |
| `GET /api/admin/security-events` | `security.read` | paginated security events | `{items,total}` | 200, 401, 403, 422 |
| `PATCH /api/admin/security-events/{id}` | `security.write` | change event status | `{"status":"resolved"}` | 200, 401, 403, 404, 422 |
| `GET /api/admin/system-health` | `dashboard.read` | service health snapshot | `{services,note}` | 200, 401, 403 |
| `GET /api/admin/notifications` | authenticated | current notifications | `{items}` | 200, 401 |
| `GET /api/admin/settings` | `settings.read` | non-secret settings | `{items}` | 200, 401, 403 |
| `PATCH /api/admin/settings/{key}` | `settings.write` | update allow-listed setting | `{"value":"..."}` | 200, 400, 401, 403, 404, 422 |
| `GET /api/admin/reports` | `reports.export` | generated report history | `{items}` | 200, 401, 403 |
| `POST /api/admin/reports/generate` | `reports.export` | generate privacy-safe aggregate report | `{"report_type":"prediction_summary","format":"json"}` | 200, 400, 401, 403, 422 |

Never place passwords, JWTs, refresh tokens, database URLs, raw customer inputs, or secret keys in examples, logs, screenshots, or issue reports.
