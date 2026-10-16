# Day 2 OpenFHE CKKS Design

CKKS is used because the standardized customer features, logistic-regression weights, bias, and logit are real-valued. CKKS represents them approximately, so the decrypted result is expected to be close to—not bit-for-bit identical to—the plaintext result.

The prototype models two trust boundaries in one executable:

1. The client owns the raw values, applies the Day 1 preprocessing, encodes and encrypts the seven scaled features using the public key, and retains the secret key.
2. The server receives only seven ciphertexts and public model parameters. It multiplies each ciphertext by its plaintext model weight, adds the weighted ciphertexts, and adds the plaintext bias.
3. The client decrypts the returned encrypted logit.

The server evaluation function has no secret-key parameter. Evaluation keys are generated for homomorphic operations and may be provided to the server; they do not grant decryption capability.

The exact sigmoid is not evaluated homomorphically in Day 2. This phase proves only the encrypted linear computation `z = w dot x + b`. Polynomial sigmoid approximation belongs to the next phase.

