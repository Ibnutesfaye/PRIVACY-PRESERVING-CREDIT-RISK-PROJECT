# Day 2 Homomorphic-Encryption Report

## Scope

Day 2 implements OpenFHE CKKS key generation, encoding, encryption, ciphertext-by-plaintext multiplication, ciphertext addition, encrypted logistic-regression weighted-sum evaluation, client decryption, and plaintext-versus-FHE verification.

It does not evaluate the sigmoid homomorphically. The encrypted output is the logistic-regression logit `z = w dot x + b`. Polynomial approximation is a later phase.

## Test input

The input is sample index 0 from the saved Day 1 test split. The seven values are already transformed with the training-fitted median imputer and `StandardScaler`:

```text
[ 0.04305900405397942,
 -0.14847433927778664,
  0.061604632254462846,
 -0.6668201284109923,
  1.515878202377027,
 -0.662679459524403,
  0.049891221778167134 ]
```

The source sample's target is class 0. The conventional exact-sigmoid probability is approximately `0.3201617828`, but that sigmoid calculation is not part of the encrypted server evaluation.

## Key boundary

- Client: public key, secret key, raw/preprocessed customer values, encryption, and decryption.
- Server: ciphertext features, plaintext model weights/bias, crypto context, and evaluation material.
- The C++ server function does not accept or access the secret key.

Evaluation keys do not provide the ability to decrypt. This prototype creates a multiplication evaluation key for completeness, although the current ciphertext-by-plaintext weighted sum does not require ciphertext-by-ciphertext relinearization.

## Measured result

| Measurement | Value |
| --- | ---: |
| Scheme | CKKS |
| Ring dimension | 16,384 |
| Encrypted features | 7 |
| Plaintext logit | -0.75302841458015779 |
| Decrypted FHE logit | -0.75302841458004366 |
| Absolute error | 1.14130926931466e-13 |
| Relative error | 1.51562576818696e-13 |
| Acceptance tolerance | 1e-6 |
| Result | PASS |

These are measured outputs from this machine and are not invented example values. CKKS is approximate; a future run may differ slightly because encryption is randomized, while remaining within the declared tolerance.

## Conclusion

The server evaluated the trained model's linear component over encrypted customer features and returned an encrypted logit. Client decryption matched the normal mathematical computation within CKKS approximation error.
