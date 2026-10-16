# System workflow

## Production ciphertext inference

```text
trusted client: validate → impute/scale → CKKS encode/encrypt
    → authenticated POST of seven ciphertexts
FastAPI: validate profile/count/size → isolated temporary request
    → evaluator process (context + evaluation keys + ciphertexts only)
    → result ciphertext → privacy-safe metadata/FHE metric
trusted client: decrypt → interpret threshold/model recommendation
    → authorized application workflow → separate human decision
```

Temporary ciphertext files live under `backend/.runtime`, are ignored, and are removed after evaluation. Structured logs contain request ID, method, route template, status, and duration only. The server does not receive plaintext features or decrypt the production result.

## Application states

`DRAFT → SUBMITTED → PREDICTION_PENDING → PREDICTED → UNDER_REVIEW → APPROVED/REJECTED` is the main path. Additional-information and cancellation transitions are explicitly allowed. State skipping is rejected. Every change records actor/time/from/to/reason and increments an optimistic version. A final decision uses a separate endpoint/permission; a decision contrary to the model recommendation requires an override reason.

## Administrator session

Login verifies normalized identity and Argon2id after rate/lockout checks. A short access JWT stays in memory; an opaque rotating refresh secret stays in session storage and only its hash is persisted. Every protected request reloads current account roles/permissions. Organization/branch membership is then enforced against the resource. Logout revokes the refresh record and is audited.

## Failure behavior

- Schema/bounds: 422 before native work.
- Authentication/permission/scope: structured 401/403.
- Version/transition conflict: 409.
- Evaluator profile/unavailability: safe 503; no native stderr/path.
- Database unavailable: readiness 503 and pool disposal on failed readiness check.
- Legacy plaintext compatibility endpoint: 404 when disabled, and forbidden at production startup.
