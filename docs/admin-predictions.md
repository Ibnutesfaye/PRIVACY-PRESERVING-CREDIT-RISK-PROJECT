# Admin Phase 5: Privacy-Safe Prediction Monitoring

Migration `20260805_0002` adds `prediction_metadata`. It stores anonymous/public identifiers, coarse risk bands, processing statuses, model and CKKS profile identifiers, stage timing, ciphertext-size metadata when available, request status, and safe error codes.

It does **not** store raw inputs, exact risk scores, raw feature vectors, ciphertext contents, IP-derived customer identities, decrypted values, passwords, tokens, or cryptographic keys.

Protected endpoints:

- `GET /api/admin/predictions` with server-side pagination, search, filters, latency range, date range, and allowlisted sorting
- `GET /api/admin/predictions/{prediction_id}`
- `GET /api/admin/predictions/{prediction_id}/timeline`
- `GET /api/admin/predictions/export` with `predictions.export`, a 5,000-row safety limit, and audit logging

Successful `/predict` calls save safe completion metadata. Evaluator failures save a generic `FHE_EVALUATION_FAILED` code and do not expose subprocess output to API clients. Validation failures occur before prediction execution and are not currently represented in prediction metadata.

The React page provides debounced search, filters, pagination, status/risk badges, safe CSV export, empty/loading/error states, and a detail drawer with privacy checks, timing, configuration, and processing timeline.
