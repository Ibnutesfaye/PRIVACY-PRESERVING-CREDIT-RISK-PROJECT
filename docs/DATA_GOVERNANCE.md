# Data classification, minimization, consent, and retention

| Data | Classification | Persistence |
|---|---|---|
| Raw customer financial features | Restricted | Never by production ciphertext API |
| Client secret key / decrypted score | Restricted | Client only; never server/database |
| Ciphertexts | Confidential | Ephemeral evaluator temporary directory |
| Customer reference | Restricted | SHA-256 reference only |
| Consent evidence | Confidential | Evidence hash and lifecycle metadata |
| Application/workflow/decision note | Confidential | PostgreSQL, scoped and audited |
| Model/profile IDs, latency, size, status | Internal | PostgreSQL/Prometheus |
| Health/liveness | Internal/public-by-policy | No secrets or customer data |

Consent records carry purpose, lawful basis, evidence hash, grant/withdrawal/expiry state. Applications require an active consent reference. Operational records carry retention expiry/policy metadata. Legal holds must block deletion. The current pilot stores retention policy configuration but does not automatically purge records; enforcement must be approved, dry-run, audited, reversible where required, and tested against legal obligations before activation.

Temporary ciphertext directories are automatically removed after each request. Logs use allow-listed operational fields only. Report exports require permissions and audit events. No raw financial feature belongs in logs, exception text, audit metadata, analytics, screenshots, or support tickets.
