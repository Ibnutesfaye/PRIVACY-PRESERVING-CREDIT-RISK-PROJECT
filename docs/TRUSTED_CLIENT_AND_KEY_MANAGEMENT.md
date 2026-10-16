# Trusted client and pilot key management

The encrypted production path uses the Python desktop/local-service package in `trusted_client/`. The browser is not a cryptographic trust boundary and does not hold the CKKS secret key. Raw applicant values are imputed, ordered, and scaled locally using the training-fitted artifacts. The client invokes OpenFHE encryption locally, sends exactly seven ciphertexts to `/api/v1/fhe/evaluate`, receives one result ciphertext, and decrypts it locally.

## Pilot custody workflow

1. An authorized institution operator runs `python -m trusted_client init-keys` on the trusted device.
2. The command writes `context.bin`, `public-key.bin`, and `evaluation-mult-keys.bin` to the public provisioning bundle. It writes `secret-key.bin` only to the selected private directory.
3. The operator provisions only the public bundle to the evaluator under the matching profile and model version. The service readiness check fails if a secret key appears in that server directory.
4. The private directory must be on institution-managed encrypted storage, restricted by OS ACL to the service identity, excluded from synchronization and backups unless the backup is an approved encrypted vault.
5. For backup, escrow the secret key in the institution's HSM/KMS/vault under dual control. The repository provides a `KeyStore` boundary for a future vendor adapter; it does not provide homemade key wrapping.
6. Rotate by generating a new profile identifier and key set, provisioning new evaluation material, validating equivalence, switching clients, and then revoking the old profile. Never overwrite an active profile in place.
7. Revoke by disabling the profile at the evaluator and removing public/evaluation material after retention approval. Existing ciphertexts cannot be decrypted without the corresponding client key.
8. For device replacement, restore the escrowed key only through the institution's custody process or create a new profile. A lost key without approved escrow is unrecoverable by design.
9. The client submits both `profile_id` and `model_version`; the evaluator rejects an incompatible contract.

`LocalDirectoryKeyStore` is suitable only for a controlled pilot with encrypted disks and managed ACLs. Production custody requires an institution-approved HSM, KMS, or secure vault adapter and an operational ceremony reviewed by security and compliance.

## Operational ceremony and accountability

- **Roles:** a key-custody officer and independent security witness generate/restore/destroy keys; a platform operator receives only public/evaluation material; a model-risk owner approves the model/profile compatibility; an auditor reviews evidence. No single evaluator administrator may obtain the client secret.
- **Generation:** record ceremony ID, key/profile/model versions, device identity, operators, timestamps, approved binary hashes, public artifact hashes, and outcome. Never record key bytes, passwords, tokens, or raw applicant data.
- **Versioning:** use immutable profile identifiers. The API binds requests to profile, model version, and the SHA-256 fingerprint of the active serialized context. The fingerprint prevents accidental profile mismatch but is not a substitute for authenticated transport or key custody.
- **Distribution:** transfer only `context.bin`, `public-key.bin`, `evaluation-mult-keys.bin`, and `profile.json` over the approved integrity-checked channel. Readiness must fail if `secret-key.bin` is present server-side.
- **Rotation/revocation:** create and validate a parallel version, authorize client cutover, disable the old profile, retain or destroy old keys according to outstanding ciphertext/record policy, and audit each transition. Do not overwrite a profile in place.
- **Compromise:** stop encrypted intake for that profile, revoke access/session credentials, isolate the device, preserve evidence, create a new key/profile, assess stored ciphertext exposure, and follow notification policy. Server-side evaluation material cannot decrypt customer data.
- **Loss/replacement:** recover only from dual-controlled institutional escrow. Without escrow, ciphertext under the lost key is unrecoverable. A replacement device receives a new profile unless policy explicitly authorizes restore.
- **Backup/destruction:** use an approved HSM/KMS/vault export/escrow mechanism and tested recovery ceremony. Destruction requires dual control, documented media/key-version retirement, and confirmation that no required ciphertext remains.
- **Audit events:** record key lifecycle action, non-secret key/profile ID, actor roles, device, result, approval/change ticket, and artifact hashes in the institutional audit system—not the financial-feature database.

The `KeyStore` protocol is the application seam for pilot local custody. A production HSM/KMS integration must be vendor reviewed and may require changing the native OpenFHE boundary so a non-exportable key can be used without materializing a filesystem key. No such integration is claimed today.
