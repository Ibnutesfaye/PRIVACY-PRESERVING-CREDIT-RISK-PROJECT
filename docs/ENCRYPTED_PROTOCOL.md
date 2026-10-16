# Ciphertext-only inference protocol

## Security boundary

Protocol version 1 separates cryptographic responsibilities by process and by artifact path:

| Operation | Required material | Forbidden material |
|---|---|---|
| `setup` (trusted client) | New CKKS context | Existing production secret keys |
| `encrypt` (trusted client) | Context, public key, scaled features | Evaluation service access |
| `evaluate` (server) | Context, multiplication evaluation keys, seven feature ciphertexts | Secret key, plaintext or scaled features |
| `decrypt` (trusted client) | Context, secret key, result ciphertext | Server-side execution |

The native command is `openfhe/day2-build-local/fhe_protocol.exe`. The server invokes only its `evaluate` command. The server profile directory is rejected as ready if it contains `secret-key.bin`.

## API contract

`GET /api/v1/fhe/profiles/current` returns non-secret profile metadata. The context and public key are available from the allow-listed artifact endpoint; evaluation keys and secret keys are never distributed there.

`POST /api/v1/fhe/evaluate` accepts:

- protocol version `1`;
- the active profile identifier;
- the active model version;
- a batch size from 1 through 8,192;
- exactly seven Base64-encoded OpenFHE ciphertexts in the declared feature order.

The server enforces both HTTP body and decoded-ciphertext limits. It writes the ciphertexts into an isolated temporary directory, invokes the evaluator with context and multiplication-key paths, and returns a Base64-encoded result ciphertext. It neither computes nor returns a plaintext risk score.

## Encrypted circuit and active parameters

With scaled features `x[0..6]`, the evaluator computes only on CKKS ciphertexts:

`z = 0.04532915891805543*x0 - 0.004971391043297565*x1 - 0.10685566608167416*x2 - 0.5493410143686471*x3 + 0.9448311085798077*x4 + 1.2425285058756619*x5 - 0.030814638728595172*x6 - 1.7227605924793603`

It then evaluates the degree-seven odd polynomial:

`p(z) = 0.50000000000000755 + 0.2351734039561946*z - 0.012339842621857708*z^3 + 0.00039426355902358648*z^5 - 0.0000047453784873149767*z^7`.

The powers are formed as `z2=z*z`, `z3=z2*z`, `z5=z3*z2`, and `z7=z5*z2`; the configured depth is six. OpenFHE `FLEXIBLEAUTOEXT` performs automatic CKKS rescaling/modulus switching. The implementation explicitly sets and the `setup` command emits: OpenFHE 1.5.1, CKKS, `HEStd_128_classic`, ring dimension 32,768, depth 6, scaling modulus 50 bits, first modulus 60 bits, batch capacity 8,192, `FLEXIBLEAUTOEXT`, and `HYBRID` key switching. These parameters support the measured circuit range, but require independent institutional cryptographic review.

## Verified result

The fresh 2026-08-07 verification generated new keys and ciphertexts for 247 diverse held-out applicants. Plain circuit versus decrypted FHE mean/median/maximum absolute errors were `1.4957957078307398e-11`, `2.766911699758623e-12`, and `1.758237999638368e-10`; standard deviation was `3.0080200572426827e-11`. Classification agreement was 100% with zero threshold crossings. The selected logit range was `[-5.462189490757259, 5.505698605265037]`; polynomial scores can slightly exceed `[0,1]` at these extremes and should be presentation-clamped after client decryption.

## Remaining pilot requirements

- The trusted desktop/local client package now performs preprocessing, key generation, encryption, submission, and decryption. Institutional packaging/signing and HSM/KMS custody remain approval gates; the React browser intentionally does not hold keys.
- APIs are authenticated and permission protected; shared distributed quotas/rate limiting remain an infrastructure gate.
- The local keystore abstraction is pilot-only and relies on institution-managed encrypted storage and ACLs.
- A separately generated context with identical CKKS parameters is serialization-compatible; ciphertext-to-profile cryptographic binding needs further protocol review.

### Same-parameter context analysis

OpenFHE context serialization describes cryptographic parameters; it is not, by itself, a unique key-pair identity. Consequently, a newly generated context with the same CKKS parameters can deserialize the ciphertext structure. This does not allow decryption: decryption still requires the matching secret key, and evaluation with an unrelated evaluation/public key fails in executable tests. The operational risk is accidental profile mixing and confusing failure behavior, not recovery of plaintext.

Protocol version 1 now requires a lowercase SHA-256 fingerprint of the exact active `context.bin` together with profile and model version. The trusted client derives it locally; the API compares it in constant time with its active context before invoking OpenFHE. This prevents accidental alternate-context submission and is covered by regression tests. It does not authenticate a malicious client's ciphertext or provide a cryptographic proof that ciphertext bytes were created under that context. TLS, caller authentication, authorization, immutable profile provisioning, artifact-signature/hash verification, and matching OpenFHE key tags remain required. No custom cryptographic primitive was introduced.
- Transport must use TLS even though feature values are encrypted, because metadata and integrity still matter.
