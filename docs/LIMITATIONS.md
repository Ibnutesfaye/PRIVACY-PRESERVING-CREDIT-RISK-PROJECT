# Limitations and prohibited claims

## Cryptographic

- CKKS is approximate and the degree-7 sigmoid is an approximation.
- The experiment demonstrates confidentiality from the evaluator, not verifiable computation, model confidentiality, or protection from a malicious client.
- The public/evaluation profile is not secret, but must be integrity-controlled and version-matched.
- Production client key generation, KMS/HSM custody, rotation, revocation, recovery, and device trust are not implemented.
- The React browser is not an audited OpenFHE client. The legacy plaintext gateway is development-only and prohibited in production configuration.

## Model and data

- Only seven numerical features are used; categorical information is excluded.
- The dataset is limited, historical, imbalanced, and not established representative of a target institution/population.
- Class-1 recall is 39.63% at threshold 0.5.
- Calibration, subgroup fairness, drift, stability, adverse-action suitability, causal interpretation, and regulatory validation are incomplete.
- A risk score or LOW/HIGH class is not a loan approval decision.

## Application and operations

- OIDC/SSO/MFA, centralized distributed rate limiting, Redis-backed FHE queues, automatic retention enforcement, and customer/device identity integration remain pilot integrations.
- The in-process login limiter does not coordinate multiple API replicas.
- Model/profile downloads and ciphertext traffic are large; capacity must be measured on target infrastructure.
- Docker and k6 are unavailable on the development workstation, so live container and 100-user acceptance are pending CI/target infrastructure.
- Backups have tooling and a runbook, but recovery objectives and a real restore rehearsal require institutional approval/infrastructure.

Do not claim that CipherScore is fully production-ready, regulator-approved, fair, anonymous, zero-knowledge, breach-proof, or suitable for autonomous lending.
